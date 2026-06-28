# Design: real-data-source

## 概述

在 `MarketDataSource` 抽象之上新增真实数据接入能力。基于用户决策采用：
1. **`AkShareSource`** — 真实数据适配器（akshare 库）
2. **`CachedSource`** — 装饰器，包装任意 `MarketDataSource` 提供 SQLite 缓存
3. **`DynamicPoolEntry`** SQLModel 表 — 全市场 ETF 持久化 + 启停
4. **环境变量 + per-request 覆盖** — 灵活切换 fixture/akshare
5. **`RetryWithBackoff`** — akshare 调用韧性（3 次重试 + 指数退避 + fixture 降级）

## 技术方案

### 方案对比

| 维度 | 备选 | 选定 |
|---|---|---|
| 缓存架构 | 装饰器 / 手写混 / 路由层 | **装饰器**（CachedSource 透明包装） |
| 动态池存储 | SQLModel / 实时拉 / JSON | **SQLModel**（持久化 + is_enabled） |
| 源切换 | 全局环境变量 / per-request / 双源并行 | **环境变量默认 + per-request 覆盖** |
| akshare 韧性 | 仅超时 / 重试+降级 / 透传 | **重试+降级**（3 次指数退避 → fixture 降级） |

### 选定的最终架构

```
┌────────────────────────────────────────────────────────────────┐
│  api/{screening,backtest,market}.py (路由层)                   │
│   ↓ _make_source(source: str | None)                           │
│   └─ ETF_DATA_SOURCE env var or per-request ?source=           │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
   ┌─────────────────────────────────────┐
   │  Source Selector (data_sources/__init__) │
   │   - "akshare" → CachedSource(AkShareSource)   │
   │   - "fixture" → FixtureCSVSource              │
   └────────────┬────────────────────────────┘
                │
                ▼ (when akshare selected)
   ┌──────────────────────────────────────┐
   │  CachedSource (decorator)            │
   │   - read-through 模式                │
   │   - 命中：market_bar_cache 表          │
   │   - 未命中：调用内层 source            │
   │   - 计数：hit_count / miss_count      │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │  AkShareSource (真实数据)            │
   │   - RetryWithBackoff 装饰            │
   │   - akshare.fund_etf_hist_em          │
   │   - akshare.fund_etf_name_em          │
   │   - 失败 → 降级 FixtureCSVSource     │
   └──────────────────────────────────────┘
```

## 详细设计

### 1. 数据模型

#### SQLModel 表：`MarketBarCache`（新增）

`backend/app/models/market_bar_cache.py`

```python
class MarketBarCache(SQLModel, table=True):
    """Per-(code, date) OHLCV cache row."""
    code: str = Field(primary_key=True, index=True)
    date: date = Field(primary_key=True, index=True)
    open: float
    high: float
    low: float
    close: float
    volume: float
    money: float | None = None
    cached_at: datetime  # 写入时间，用于 TTL
    source: str = "akshare"  # 标记写入源（暂只 akshare）
```

- 主键：`(code, date)` 复合
- 索引：`code`、`date` 单独索引便于窗口查询
- 暂不实现 TTL 过期（手工调用清空）

#### SQLModel 表：`DynamicPoolEntry`（新增）

`backend/app/models/dynamic_pool.py`

```python
class DynamicPoolEntry(SQLModel, table=True):
    """全市场 ETF 池条目（akshare 同步）。"""
    code: str = Field(primary_key=True, index=True)
    name: str
    is_enabled: bool = Field(default=False)  # 默认不启用；用户手动开启
    last_synced_at: datetime
```

- 拉取：覆盖式写入（akshare 每次返回全市场，UPSERT）
- 默认 `is_enabled=False`：必须用户在前端显式开启，避免一次性引入过多标的
- 与 `StaticPoolEntry` 在 `filter_etfs` 层融合（已存在 `dynamic_pool` 参数）

### 2. AkShareSource 适配器

`backend/app/data_sources/akshare_source.py`

```python
class AkShareSource(MarketDataSource):
    """Wraps akshare fund_etf_* functions."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        # fixtures_dir 用于降级 fallback
        self._fallback = FixtureCSVSource(fixtures_dir) if fixtures_dir else None

    def history(self, code, start, end, fields=None) -> pd.DataFrame:
        df = retry_with_backoff(
            lambda: _akshare_history(code, start, end),
            max_retries=3,
            backoff_factor=2.0,
        )
        return _normalize_columns(df, fields)

    def snapshot(self, code, as_of) -> dict[str, float]:
        # 取最后一行；同 history 但只取 row
        ...

    def all_etfs(self, as_of) -> list[str]:
        # akshare.fund_etf_name_em() → DataFrame(code, name)
        df = retry_with_backoff(akshare.fund_etf_name_em)
        return df["code"].tolist()
```

字段映射：akshare `fund_etf_hist_em` 返回 `[日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率]` → 重命名为 `[date, open, close, high, low, volume, money, ...]`。

降级策略：所有 akshare 调用失败后 → `_fallback.history/snapshot/all_etfs`，仅当 `fixtures_dir` 提供时才降级。

### 3. CachedSource 装饰器

`backend/app/data_sources/cache.py`

```python
class CachedSource(MarketDataSource):
    """Read-through cache wrapping another MarketDataSource."""

    def __init__(self, inner: MarketDataSource, db_path: Path) -> None:
        self.inner = inner
        # 用 SQLAlchemy 直接操作（不走 SQLModel session 简化）
        self._engine = create_engine(f"sqlite:///{db_path}")

    def history(self, code, start, end, fields=None):
        # 1) 查 cache for [start, end]
        cached = _read_cache(code, start, end)
        # 2) 缺失日期 = [start, end] - cached_dates
        missing_dates = _diff_dates(start, end, cached)
        if missing_dates:
            # 3) 调 inner 拿整段（含已缓存的日期也行）
            new_df = self.inner.history(code, start, end)
            # 4) 仅写入缺失日期
            _write_cache(code, new_df.loc[missing_dates])
        # 5) 返回 [start, end] 合并视图
        return _read_cache(code, start, end, fields)

    def snapshot(self, code, as_of):
        # 1) 查 cache for (code, as_of.date())
        cached = _read_one(code, as_of.date())
        if cached:
            self._hit_count += 1
            return cached
        # 2) 调 inner，写 cache
        snap = self.inner.snapshot(code, as_of)
        _write_one(code, as_of.date(), snap)
        self._miss_count += 1
        return snap

    def stats(self) -> dict:
        return {"hit": self._hit_count, "miss": self._miss_count}
```

设计要点：
- **装饰器模式**：不动 `AkShareSource`、不动 `FixtureCSVSource`，`CachedSource` 透明叠加
- **计数器**：`stats()` 方法暴露给 `/api/health` / 数据源面板
- **TTL**：暂不实现；接口预留 `clear()` 供前端"清空缓存"

### 4. 源选择器

`backend/app/data_sources/__init__.py`（新增模块）

```python
def make_source(name: str | None = None) -> MarketDataSource:
    """Build a MarketDataSource by name.
    
    name 为 None 时使用 ETF_DATA_SOURCE 环境变量（默认 'fixture'）。
    """
    selected = (name or os.environ.get("ETF_DATA_SOURCE", "fixture")).lower()
    if selected == "fixture":
        return FixtureCSVSource(FIXTURES_DIR)
    if selected == "akshare":
        akshare = AkShareSource(fixtures_dir=FIXTURES_DIR)  # for fallback
        cached = CachedSource(akshare, db_path=DB_PATH)
        return cached
    raise ValueError(f"Unknown source: {selected}")
```

3 处 `_market()` 工厂改为调用 `make_source(source)`：
```python
@router.get("/history")
def market_history(code: str, ..., source: str | None = None):
    market = make_source(source)
    df = market.history(code, start, end, fields=requested)
    ...
```

### 5. 动态池端点

`backend/app/api/configs.py`（追加）

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/configs/pool/dynamic` | 列出所有 `DynamicPoolEntry` |
| POST | `/api/configs/pool/dynamic/sync` | 调用 akshare 拉取全市场、UPSERT 写入 |
| PATCH | `/api/configs/pool/dynamic/{code}` | 切换 `is_enabled` |

`POST /sync` 行为：
1. 调用 `akshare.fund_etf_name_em()`
2. 转 `[(code, name)]` 列表
3. 对每行 UPSERT（保留 `is_enabled`，更新 `last_synced_at`）
4. 返回 `{synced: N, total: M, enabled: K}`

`filter_etfs` 融合：现有 M2 已支持 `dynamic_pool` 参数。`/api/screening/today` 与 `/api/backtest` 调用时，传入 `[e.code for e in DynamicPoolEntry if e.is_enabled]`。

### 6. 韧性：`RetryWithBackoff`

`backend/app/data_sources/retry.py`

```python
def retry_with_backoff(fn, max_retries=3, backoff_factor=2.0, initial_delay=1.0):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries:
                raise
            sleep(initial_delay * (backoff_factor ** attempt))
    raise RuntimeError("unreachable")
```

akshare 临时错误（网络、超时、限速）一律捕获重试；参数错误（code 不存在）不重试直接抛。

### 7. 前端：`DataSource.tsx`

```
┌──────────────────────────────────────────┐
│  数据源                                    │
├──────────────────────────────────────────┤
│  当前源：[Fixture ▼]                      │
│  [切换为 akshare]  (需环境变量启动时支持)   │
│                                           │
│  缓存统计 (akshare only):                  │
│    命中：1234                              │
│    未命中：56                              │
│    命中率：95.6%                           │
│    [清空缓存]                              │
│                                           │
│  末次同步：2026-06-28 14:30 (3 分钟前)     │
│  [立即同步]                                │
│                                           │
│  动态池：                                  │
│    已同步：523 只 ETF                       │
│    已启用：12 只  (用户在表格勾选)           │
│    [查看动态池]                             │
└──────────────────────────────────────────┘
```

TanStack Query 拉取 `/api/health?stats=1` 与 `/api/configs/pool/dynamic`；切换/同步按钮调对应 POST/PATCH。

### 8. 配置与默认值

`.env.example` 追加：
```
# 数据源选择：fixture | akshare （默认 fixture）
ETF_DATA_SOURCE=fixture
```

`backend/app/config.py`（新建轻量配置模块，env var loader）

## 风险与应对

| 风险 | 应对 |
|---|---|
| akshare 偶发抽风（接口限速、改字段） | 重试+降级到 fixture；接口契约层做字段映射与回退 |
| akshare 未装（开发环境无网络/装包失败） | 导入 try/except；`ETF_DATA_SOURCE` 默认 fixture，akshare 仅按需加载 |
| 缓存表膨胀（每只 ETF × 250 天/年 × N 年） | 提供 `clear()` 接口；规范化为单 DB；不实现自动 TTL（避免误删） |
| 动态池全市场 ~500+ ETF 拉一次耗时 | 后台线程跑同步、API 异步返回；前端显示进度 |
| akshare 返回字段变化（库版本升级） | 在 `_normalize_columns` 集中映射；测试覆盖字段重命名 |
| fixture 改 akshare 后测试需要改 `MarketDataSource` 实例化 | 用 `make_source("fixture")` 全局替换，3 处工厂同步改 |

## 实施顺序（spec 阶段展开）

1. 数据模型：`MarketBarCache` + `DynamicPoolEntry` + 初始化
2. `RetryWithBackoff` 工具
3. `AkShareSource` + 字段映射
4. `CachedSource` + 缓存表读写
5. `make_source` 选择器 + 替换 3 处 `_market()` 工厂
6. 动态池 API（GET/sync/PATCH）
7. 前端 `DataSource.tsx` + 路由挂载
8. 测试：3 个新测试文件 + 74 个旧测试全过
9. README 更新 + 配置更新

## 出口

设计已收敛 4 个关键决策。下一步进入 `spec` 阶段，将本设计展开为 `spec.md`（OpenSpec 格式）+ `plan.md`（checkbox 实现计划）。

# 架构设计

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│  React 前端 (frontend/)                              │
│  - 配置面板（池子/词典/参数）                          │
│  - 回测可视化                                       │
│  - 当日信号 & 持仓展示                                │
└────────────────────┬────────────────────────────────┘
                     │ HTTP/JSON
┌────────────────────▼────────────────────────────────┐
│  Python 后端 (backend/)                              │
│  - FastAPI 路由层                                    │
│  - Service 层（筛选/回测/信号）                       │
│  - Data Source 抽象层（行情、配置持久化）               │
│  - 收盘同步定时任务                                   │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    SQLite DB    行情数据源    文件/对象存储
    (配置/历史)
```

## 技术选型

| 层 | 技术 | 理由 |
|---|------|------|
| 前端框架 | React + Vite | 用户指定 |
| 前端 UI | Ant Design 或 shadcn/ui | 适合配置型后台 |
| 前端状态 | TanStack Query + Zustand | Query 管远程，Zustand 管本地 UI 状态 |
| 后端框架 | FastAPI | 异步友好、Pydantic 校验、自动 OpenAPI |
| 后端 ORM | SQLModel（基于 SQLAlchemy + Pydantic） | 与 FastAPI 风格一致 |
| 数据库 | SQLite（dev）→ Postgres（prod） | 起步轻量、迁移成本低 |
| 数值计算 | pandas + numpy | 与原策略代码一致 |
| 测试 | pytest + httpx（异步测试） | TDD 强制 |

## 模块划分（backend）

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── api/               # 路由层
│   │   ├── configs.py     # 池子/词典/参数 CRUD
│   │   ├── screening.py   # ETF 筛选 / 当日信号
│   │   ├── backtest.py    # 回测
│   │   ├── market.py      # 历史数据
│   │   └── portfolio.py   # 持仓
│   ├── services/          # 业务逻辑
│   │   ├── screening.py   # filter_etfs() 核心（从 main.py 迁移）
│   │   ├── backtest.py    # 回测引擎
│   │   └── signals.py     # 调仓建议生成
│   ├── data_sources/      # 数据源抽象
│   │   ├── base.py        # MarketDataSource 接口
│   │   └── mock.py        # mock 实现
│   ├── models/            # SQLModel ORM
│   ├── schemas/           # Pydantic 请求/响应模型
│   └── sync/              # 收盘同步任务
└── tests/
```

## 模块划分（frontend）

```
frontend/
├── src/
│   ├── pages/
│   │   ├── PoolConfig.tsx       # 静态池配置
│   │   ├── ThemeConfig.tsx      # 主题词典配置
│   │   ├── StrategyConfig.tsx   # 策略参数配置
│   │   ├── Backtest.tsx         # 回测页
│   │   ├── Signals.tsx          # 当日买卖信号
│   │   └── Portfolio.tsx        # 持仓展示
│   ├── api/                     # 后端 API 客户端
│   ├── components/              # 复用组件
│   └── store/                   # Zustand stores
└── ...
```

## 数据流

### 当日信号流

1. 前端调用 `GET /api/signals/today`
2. 后端从 DB 读取池子/词典/参数配置
3. 后端调用 `screening.filter_etfs()` → 返回目标列表
4. 后端结合当前持仓生成调仓建议（卖出列表、买入列表、数量）
5. 返回 JSON 给前端展示

### 回测流

1. 前端调用 `POST /api/backtest`（区间、初始资金、配置快照）
2. 后端在区间内按日重放筛选 + 调仓逻辑
3. 返回净值序列、交易明细、统计指标

## 关键设计决策

- **配置存储**：前端写入的池子/词典/参数持久化到 DB，回测时可指定配置快照（避免回测结果随当前配置漂移）
- **数据源抽象**：所有行情访问通过 `MarketDataSource` 接口，便于从 mock 切换到 akshare/tushare/聚宽
- **筛选逻辑纯净化**：迁移 `main.py` 的 `filter_etfs()` 时去除对 JoinQuant 全局函数（`history`、`get_current_data` 等）的依赖，改为显式参数注入，便于单测

## 实施调整（M0–M8 bootstrap-fullstack，2026-06-28）

- **持仓聚合**：原设计 `portfolio.py` 路由改为在 `screening.py` 路由内一并暴露 `GET /api/portfolio` 与 `GET /api/signals/today`（聚合 `portfolio_mock` + `signals.generate_signals`，简化模块边界）
- **同步落盘而非入库**：原设计同步写 DB，改为写 `data/daily_sync/YYYY-MM-DD.json`（轻量；生产可平迁到 DB）
- **回测任务异步化**：通过 FastAPI `BackgroundTasks` + JSON 文件持久化（`data/backtest_tasks/{task_id}.json`），前端按 2s 轮询 `/api/backtest/{task_id}` 获取状态
- **JoinQuant 兼容验证**：保留 `main.py` 不动，新增 `tests/_jq_shim.py` 装载原文件并 stub 所有 JQ API，用 3 个对照测试（default / industry-diverse / ma-filter-off）验证迁移后 `filter_etfs` 与原行为一致
- **前端 UI**：实际采用 Tailwind + 自写小组件替代 shadcn（避免额外工具链），仍满足配置型后台形态

## 实施调整（M9 real-data-source，2026-06-29）

### 数据源抽象层

```
backend/app/data_sources/
├── base.py              # MarketDataSource 抽象接口（新增 all_etf_entries）
├── fixture.py           # FixtureCSVSource（GBM mock）
├── akshare_source.py    # AkShareSource（真实 akshare 适配）
├── cache.py             # CachedSource（读穿透缓存装饰器）
├── retry.py             # retry_with_backoff（指数退避工具）
└── __init__.py          # make_source(name) 工厂 + reset_source_cache
```

**`MarketDataSource` 接口**：

- `get_etf_list(as_of) -> list[str]`：返回候选池代码
- `get_history(code, start, end) -> DataFrame`：OHLCV + amount
- `get_spot(code, as_of) -> dict`：当日快照（close/volume/amount）
- `all_etf_entries(as_of) -> list[(code, name)]`：返回 `(代码, 名称)` 列表，用于动态池同步；无名称元数据的实现可返回 `[(code, code)]`

### 数据源切换

```
请求 (per-request ?source=akshare) ──┐
                                     │
环境变量 ETF_DATA_SOURCE ────────────┼─► make_source(name) ──► MarketDataSource
                                     │   (含 LRU 缓存 +            实例
                                     │    reset_source_cache)
                                     │
默认值（fixture）────────────────────┘
```

- `make_source()` 不带参数时读 `ETF_DATA_SOURCE`，缺省 `fixture`
- `make_source("akshare")` 强制走 akshare，**自动外层包 `CachedSource`**（读穿透到 SQLite `market_bar_cache`）
- `make_source("fixture")` 不包缓存
- 所有读行情接口（`/api/market/history`、`/api/screening/today`、`/api/signals/today`、`/api/portfolio`、`/api/backtest`）均接受 `?source=` per-request 覆盖

### AkShareSource 关键细节

- **K 线**：`akshare.fund_etf_hist_em(symbol, period="daily", start_date, end_date, adjust="hfq")` → 中文列名 `日期/开盘/收盘/最高/最低/成交量/成交额` 映射为英文 `date/open/close/high/low/volume/amount`
- **全市场列表**：`akshare.fund_etf_spot_em()` → 1522 条 ETF，列 `代码/名称`（6 位裸码如 `512650`，无 `XSHG` 后缀）
- **降级策略**：构造时若传 `fixtures_dir`，K 线请求在 akshare 抛异常时回退到 fixture（开发便利）；不传则纯透传（生产用）
- **重试**：通过 `retry_with_backoff(max_retries=3, initial_delay=0.5, backoff=2.0)` 包裹调用

### CachedSource

```
请求 → SQLite market_bar_cache 查询
       ├─ 命中（区间 ⊆ 已存） → 直接返回
       └─ 未命中 → 调 inner.get_history() → 写入缓存 → 返回
```

- Key = `(source_name, code, start, end, adjust)`；命中计数器暴露 `stats() -> {hit, miss}` 与 `clear()`
- `/api/health?stats=1` 在当前默认源为 `CachedSource` 时返回 `cache_hit` / `cache_miss` 计数（fixture 模式不暴露）

### 动态池流程

```
前端 /datasource 页面
   │
   ├─ GET /api/configs/pool/dynamic        → DynamicPoolEntry 列表
   ├─ POST /api/configs/pool/dynamic/sync  → 强制调 AkShareSource()（不读 ETF_DATA_SOURCE）
   │     ├─ ImportError → 503 "akshare is not installed"
   │     ├─ 网络/解析异常 → 502 "akshare fetch failed: ..."
   │     └─ 返回空 list → 502 "akshare returned an empty ETF list"
   │     成功 → UPSERT（保留旧 is_enabled，刷新 name/last_synced_at）→ 200 {synced, total, enabled}
   └─ PATCH /api/configs/pool/dynamic/{code} → 切换 is_enabled
```

`filter_etfs` 后续需补一步：akshare 6 位裸码（如 `512650`）↔ 静态池带后缀（如 `512650.XSHG`）做归一化合并（M10 计划）。

### 前端观测面板

`/datasource` 页（`frontend/src/pages/DataSource.tsx`）：

- 顶部：健康状态 + 缓存命中/未命中计数（5s 轮询 `useHealthStats`）
- 中部：动态池表格 + 名称过滤 + 行内启用开关（`useToggleDynamicEntry`）
- 底部：「立即同步」按钮 + 「同步源: akshare」内联提示（`useSyncDynamicPool`）
- 错误展示：`ApiError.detail` 直接显示，避免「API 503:」前缀污染

## 同步进度可视化（add-sync-progress-ui 2026-06-29）

### 进程内进度跟踪器

```
backend/app/services/sync_progress.py
├── ProgressInfo (Pydantic BaseModel)
│   code / from_date / to_date / current_date
│   total_days / completed_days
│   overall_index / overall_total
│   started_at
└── SyncProgressTracker
    ├── _by_code: dict[str, ProgressInfo]
    ├── set(code, info)         # 写入或覆盖
    ├── get_all() -> list       # 返回全部 in-progress
    ├── clear()                 # 同步完成/异常时调用
    └── is_active() -> bool     # dict 非空即为 active

# module-level singleton
tracker = SyncProgressTracker()
```

**为什么是进程内单例而不是 BackgroundTasks + 状态文件**：
- 同步窗口在 mock fixture 上 < 10s（47 codes × 200 days），不需要跨重启恢复
- 避免引入 BackgroundTasks 的额外状态文件持久化层
- 测试隔离简单：测试构造独立 `SyncProgressTracker()` 实例；autouse fixture `tracker.clear()` 守护 module singleton

### 双层循环 + 整体索引

```
for code in codes:                       # 外层：code-major
    for offset in range(total_days):     # 内层：日期-major
        read_bar(code, from_date + offset)
        overall_index += 1
        tracker.set(code, ProgressInfo(...))
```

- `overall_index` 单调递增 → 前端 `Math.max(...)` 直接得「当前总步数」
- `completed_days = offset + 1` → 该 code 已完成的天数
- 单 (code, date) 异常不中断后续（per-row try/except）；`status: failed` 落盘但不更新异常文案

### 同步状态 schema

```
SyncStatusResponse
├── as_of: str | null
├── etfs: list[SyncETFStatus]                 # 既有
├── in_progress: list[ProgressInfo] | None    # 新增（None 表示未运行）
└── is_running: bool                          # 新增

SyncTriggerResult extends SyncStatusResponse
├── synced_count: int                         # 既有
├── run_at: datetime                          # 既有
├── from_date: date                           # 新增（回显入参）
└── to_date: date                             # 新增
```

- `in_progress` 与 `is_running` 均为 Optional（旧 mock 仍合法）
- `SyncTriggerResult` 把 `from_date/to_date` 回显，前端可用于错误恢复

### 前端进度流

```
DynamicPoolPage
├── DateRangePicker (modal)
│   ├── 默认 from=today-30 / to=today
│   ├── 客户端校验：from<=to + 跨度<=730（与后端 MAX_RANGE_DAYS 对齐）
│   ├── 错误：role="alert" 内联展示 detail
│   └── onConfirm({from_date,to_date}) → useTriggerSync.mutate(...)
├── useTriggerSync
│   ├── POST /api/sync/historical/trigger?from_date=...&to_date=...
│   ├── onSuccess → setQueryData + invalidate ["sync-historical-status"]
│   └── 错误 → Modal 顶部展示，按钮恢复可点
├── useSyncStatus (10s polling, refetchOnWindowFocus default)
│   └── data.in_progress → <SyncProgressBanner>
│                          └── 各 code → <RowProgressBar>
└── 按钮 disabled 条件
    ├── anyPending (mutation isPending)
    └── isRunning (status.is_running)
```

### 复用 vs 重构取舍

- **保留 `useSyncStatus` 10s 轮询**：不引入新传输层（SSE/WebSocket），复用现有架构。代价是极短同步（< 10s）可能错过进度展示，但 `refetchOnWindowFocus` 兜底
- **`SyncStatusResponse` 字段向后兼容**：`in_progress` / `is_running` 均为 Optional，旧 mock 不传也合法
- **`useTriggerSync` 签名改为必填 `{from_date, to_date}`**：单一调用方 `DynamicPoolPage`，破坏性更新受控；type-level 阻止旧调用方式编译通过
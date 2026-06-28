# Design: bootstrap-fullstack

## 概述

将原聚宽（JoinQuant）单文件 ETF 动量轮动策略 `main.py` 重构为 React 前端 + Python（FastAPI）后端的全栈应用。

策略核心逻辑（双均线过滤、动量评分、行业分散、止损、防御 ETF）保持行为不变，仅从 JoinQuant 全局函数依赖迁移为显式参数注入的后端服务。前端提供配置 UI、信号/持仓展示、回测可视化。

## 技术决策摘要

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 后端框架 | FastAPI | 异步友好、Pydantic 校验、自动 OpenAPI |
| 后端 ORM | SQLModel（SQLAlchemy + Pydantic） | 与 FastAPI 风格一致、类型安全 |
| 数据库 | SQLite（dev） | 起步轻量、零运维 |
| 回测执行 | FastAPI BackgroundTasks | 简单、足够起步；限制（重启丢失任务）可接受 |
| 实时推送 | HTTP 轮询（5s 间隔） | 信号/持仓变动频率低（日 1–2 次） |
| 认证 | 无（本地使用） | 起步范围最小，后续可加 |
| 数据源 mock | 预设 fixture CSV | 可重放、可测、零外部依赖 |
| 前端构建 | Vite + React + TypeScript | 现代默认 |
| 前端 UI | shadcn/ui | 用户选择 |
| 前端状态 | TanStack Query（远程）+ Zustand（本地 UI） | 关注点分离 |
| 回测粒度 | 日级（`frequency="1d"`） | 起步足够 |
| 筛选迁移策略 | 一次迁移 | 解耦 JoinQuant 依赖 |
| `main.py` 处理 | 迁移后保留作参考，加头部注释 | 可对照验证迁移正确性 |
| API 风格 | RESTful + JSON | 与简单后台匹配 |

## 详细设计

### 数据模型

#### 配置（持久化到 SQLite）

```sql
-- 静态核心池：每只 ETF 一行
CREATE TABLE static_pool (
  code           TEXT PRIMARY KEY,   -- ETF 代码，如 "510300.XSHG"
  display_name   TEXT,                -- 可选冗余名称
  enabled        INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);

-- 主题分类词典：每个主题多关键词（行式存储便于编辑）
CREATE TABLE theme_keyword (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  theme          TEXT NOT NULL,       -- 如 "半导体"
  keyword        TEXT NOT NULL,       -- 如 "芯片"
  UNIQUE(theme, keyword)
);

-- 策略参数（key-value，JSON 字段存复杂结构）
CREATE TABLE strategy_param (
  key            TEXT PRIMARY KEY,
  value_json     TEXT NOT NULL,       -- JSON 序列化
  updated_at     TEXT NOT NULL
);

-- 初始数据（首次启动时种入默认值，与原 main.py 保持一致）
-- 静态池：约 145 只 ETF（来自 main.py STATIC_ETF_POOL）
-- 主题词典：17 个主题（来自 main.py THEME_KEYWORDS）
-- 参数：stock_sum=1, momentum_days=25, ma_short=20, ma_long=60, stop_loss_ratio=0.92,
--       defensive_etf="511880.XSHG", dynamic_pool_size=150, volume_threshold=2.5 等
```

#### 行情/回测数据（fixture 目录）

```
backend/data/fixtures/
├── 510300.XSHG.csv       # 沪深300 ETF
├── 510500.XSHG.csv       # 中证500
├── 511880.XSHG.csv       # 银华日利（防御）
├── ...                   # 按需扩展
```

CSV 格式：

```csv
date,open,high,low,close,volume,money
2024-01-02,3.850,3.870,3.840,3.860,12345678,47654321.00
...
```

fixture 文件由迁移脚本一次性生成（使用 `numpy.random` 模拟几何布朗运动 + 真实 ETF 量级噪声），存入 git，保证可重放。

### 数据源抽象

```python
# backend/app/data_sources/base.py
class MarketDataSource(Protocol):
    def history(self, code: str, start: date, end: date, fields: list[str]) -> pd.DataFrame: ...
    def snapshot(self, code: str, as_of: datetime) -> dict: ...   # last_price, volume, money 等
    def all_etfs(self, as_of: date) -> list[str]: ...

# backend/app/data_sources/fixture.py
class FixtureCSVSource:
    """从 backend/data/fixtures/*.csv 读取，仅支持日级"""
    ...

# 工厂
def get_market_data_source() -> MarketDataSource:
    return FixtureCSVSource(fixtures_dir=settings.fixtures_dir)
```

接口设计要点：返回 `pd.DataFrame` 而非原始 dict，便于复用 numpy/pandas 逻辑。

### API 定义

所有 API 前缀 `/api`，响应统一 JSON，错误格式：

```json
{ "error": { "code": "string", "message": "string", "detail": {} } }
```

| 路径 | 方法 | 用途 |
|------|------|------|
| `/api/configs/pool` | `GET` | 列出静态池 |
| `/api/configs/pool` | `POST` | 批量新增/全量替换 |
| `/api/configs/pool/{code}` | `PUT` | 更新单只（启用/禁用） |
| `/api/configs/pool/{code}` | `DELETE` | 删除单只 |
| `/api/configs/themes` | `GET` | 列出主题词典 |
| `/api/configs/themes` | `PUT` | 全量替换词典 |
| `/api/configs/strategy` | `GET` | 获取策略参数 |
| `/api/configs/strategy` | `PUT` | 更新参数 |
| `/api/screening/today` | `GET` | 当日筛选（基于当前配置） |
| `/api/signals/today` | `GET` | 当日调仓建议（卖/买清单 + 数量） |
| `/api/portfolio` | `GET` | 当前持仓（mock 一份样例持仓） |
| `/api/backtest` | `POST` | 启动回测（异步任务） |
| `/api/backtest/{task_id}` | `GET` | 查询任务状态/结果 |
| `/api/market/history` | `GET` | 单只 ETF 历史 K 线 |
| `/api/market/list` | `GET` | 可查询的 ETF 列表 |

#### 请求/响应示例

**`GET /api/signals/today`**

```json
{
  "date": "2026-06-28",
  "current_holdings": [
    { "code": "510300.XSHG", "shares": 5000, "avg_cost": 3.85, "last_price": 3.92 }
  ],
  "to_sell": [
    { "code": "510300.XSHG", "reason": "not_in_target", "shares": 5000 }
  ],
  "to_buy": [
    { "code": "159915.XSHE", "target_value": 100000, "reason": "momentum_top1" }
  ],
  "target_list": ["159915.XSHE"],
  "config_snapshot_id": "cs_20260628_001"
}
```

**`POST /api/backtest`**

```json
// request
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 1000000,
  "config_snapshot_id": "cs_20240601_001"   // 可选，默认使用当前配置
}

// response (initial)
{ "task_id": "bt_20260628_001", "status": "pending" }

// GET /api/backtest/bt_20260628_001
// status: pending | running | done | failed
// done: 含 nav_series, trades, stats
{
  "task_id": "bt_20260628_001",
  "status": "done",
  "result": {
    "nav_series": [{ "date": "2024-01-02", "nav": 1.000 }, ...],
    "trades": [...],
    "stats": {
      "total_return": 0.187,
      "annual_return": 0.205,
      "max_drawdown": -0.082,
      "sharpe": 1.42,
      "trade_count": 48
    }
  }
}
```

### 服务层结构

```
backend/app/services/
├── screening.py        # filter_etfs() — 从 main.py 迁移
├── backtest.py         # 回放筛选 + 计算净值
├── signals.py          # 基于筛选 + 持仓生成调仓建议
└── portfolio.py        # 持仓聚合（市值、盈亏、止损线）
```

### 筛选核心迁移（filter_etfs）

迁移要点（去除 JoinQuant 全局依赖）：

| 原 JoinQuant API | 替换 |
|------------------|------|
| `attribute_history(security, n, '1d', ['close'])` | `market_data.history(security, end-date, n, ['close'])` |
| `get_current_data()` | `market_data.snapshot(codes)` 一次性批量取 |
| `get_security_info(security).display_name` | 配置中冗余存储或 `market_data.snapshot(code)["display_name"]` |
| `get_all_securities(['etf'], date)` | `market_data.all_etfs(date)` |
| `log.info/warning/error` | 标准 `logging` 模块，logger 名为 `etf_momentum.screening` |
| `context.current_dt` | 调用方传入的 `as_of: datetime` |
| `context.portfolio` | 调用方传入的 `Portfolio` Pydantic 模型 |
| 全局变量 `g_positions`, `g_buy_prices`, `g_dynamic_pool` | 移到 `ScreeningContext` 对象中，作为参数传入 |

迁出后的函数签名：

```python
def filter_etfs(
    as_of: datetime,
    static_pool: list[str],
    dynamic_pool: list[str],
    themes: dict[str, list[str]],
    params: StrategyParams,
    market: MarketDataSource,
) -> list[str]:
    """返回当日目标 ETF 列表（按 score 降序）"""
```

这样纯函数化后便于单测（注入 mock 数据 + 固定配置，验证输出）。

### 前端结构

```
frontend/
├── src/
│   ├── pages/
│   │   ├── PoolConfig.tsx       # 静态池配置（Table + 编辑/删除）
│   │   ├── ThemeConfig.tsx      # 主题词典（分组编辑）
│   │   ├── StrategyConfig.tsx   # 策略参数（Form）
│   │   ├── Signals.tsx          # 当日信号（卖/买卡片 + 表格）
│   │   ├── Portfolio.tsx        # 持仓（Table + Statistic）
│   │   ├── Backtest.tsx         # 回测（DatePicker + 触发 + 净值曲线）
│   │   └── History.tsx          # 单只 ETF 历史（K 线图）
│   ├── components/
│   │   ├── ui/                  # shadcn 生成的原始组件
│   │   └── ...
│   ├── api/
│   │   └── client.ts            # fetch 封装 + TanStack Query hooks
│   ├── store/                   # Zustand stores
│   ├── lib/
│   └── App.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

shadcn/ui 组件初始化：`npx shadcn@latest init`（按提示选择），按需添加 button/table/form/select/date-picker/card/statistic/dialog/tabs/toast。

### 回测任务存储（内存 + 文件）

为避免引入 Redis/Bull 等额外服务，回测任务状态保存在 `backend/data/backtest_tasks/{task_id}.json`：

```json
{
  "task_id": "bt_20260628_001",
  "status": "running",
  "created_at": "2026-06-28T16:00:00Z",
  "progress": { "current_date": "2024-06-15", "total_days": 250 },
  "result": null
}
```

进程重启后丢失 pending/running 任务（符合 BackgroundTasks 语义）。前端轮询时如发现 404，提示"任务已过期"。

### 错误处理

| 场景 | 行为 |
|------|------|
| 配置缺失（首次启动） | 自动种入默认值 |
| 筛选无目标 | 返回 `[]` + 警告信号，前端切换至防御 ETF 模式 |
| 回测区间无 fixture 数据 | API 返回 400，前端展示明确提示 |
| 行情 fixture 缺失 | `MarketDataSource` 抛 `DataNotFoundError`，服务层转为 404 |
| 前端 API 失败 | TanStack Query 自动重试 1 次 + toast 错误 |

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 筛选逻辑迁移引入 bug | 策略行为漂移 | 单测覆盖原行为样例；保留 `main.py` 作参照；启动时跑一次"对照测试"（fixture 输入，两条路径结果应一致） |
| fixture 数据不真实 | 回测结果无参考价值 | 文档明确"当前为示意回测"；真实数据源接入是后续变更 |
| SQLite 并发限制 | 多用户/多写阻塞 | 起步单用户足够；切换 Postgres 只需改连接串 |
| BackgroundTasks 重启丢失 | 长回测中断 | 限制单次回测 ≤ 1 年区间，任务耗时通常 < 1 分钟；后续可换 Celery |
| 前端构建失败 | 阻碍 E2E 演示 | CI 跑 `npm run build` 兜底 |
| shadcn/ui 需要 Node 18+ | 本地环境 | README 列出前置依赖 |

## 验证策略

- **M2 完成时**：核心筛选逻辑迁移后，用 3 组 fixture 输入跑对照测试（原 `main.py` vs 新实现），结果应 100% 一致
- **每个 PR**：pytest 通过 + ruff/black + tsc 编译通过
- **手动 E2E**：启动后端 → 启动前端 → 配置 → 触发回测 → 看到结果

## 后续变更（不在本次范围）

- 真实行情数据源接入（akshare/tushare/聚宽）
- 多用户认证
- 分钟级回测
- 持仓持久化（当前 mock）
- 收盘同步定时任务（M8）的真实实现
- 部署方案（Docker / 远端）
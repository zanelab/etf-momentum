# etf-momentum Backend

A 股 ETF 动量策略系统的后端服务。基于 FastAPI + SQLAlchemy 2.0 + Alembic，使用 `uv` 管理依赖，akshare 同步行情数据。

## 目录

- [项目简介](#项目简介)
- [环境要求](#环境要求)
- [安装](#安装)
- [数据库配置](#数据库配置)
- [数据库迁移](#数据库迁移)
- [启动开发服务器](#启动开发服务器)
- [运行测试](#运行测试)
- [数据模型](#数据模型)
- [CLI 命令](#cli-命令)
- [动量因子](#动量因子)
- [回测引擎](#回测引擎)
- [业绩指标](#业绩指标)
- [实时信号](#实时信号)
- [REST API](#rest-api)
- [Docker](#docker)
- [项目结构](#项目结构)
- [后续计划](#后续计划)

## 项目简介

v1.0 已交付的全部后端能力：

- **FastAPI 应用入口**（`app/main.py`）+ CORS
- **健康检查端点** `GET /health`
- **18 个 REST 端点**（`/api/v1` 前缀）：etfs / pools / signals / backtest / sync 五大模块 + CORS
- **SQLite 数据层**：4 个核心实体（ETF / DailyPrice / BacktestRun / SignalSnapshot）
- **Alembic 数据库迁移**（3 个版本：initial / nullable score+rank / nav series）
- **Repository 模式**（`EtfRepository`）封装查询
- **Session 注入**：FastAPI `Depends(get_db)`
- **akshare 数据同步**：CLI `python -m app.data.sync`（Protocol 抽象 + HTTP / Fake 双实现）
- **动量因子原语**（`app/factors/momentum`）：12-1 动量纯函数模块
- **回测引擎**（`app/backtest/`）：纯函数 `run_backtest` + 6 指标 `compute_metrics` + 持久化 `save_backtest_run`
- **实时信号**（`app/signals/` + `app/data/signal.py`）：BUY/HOLD/WATCH 三态 + CLI 落库
- **267 个 pytest 单元/集成测试**（内存 SQLite，无外部依赖）

## 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 0.11+

## 安装

```bash
cd backend
uv sync --extra dev
```

## 数据库配置

通过环境变量 `DATABASE_URL` 配置，默认 `sqlite:///./etf_momentum.db`。
可用 `backend/.env.example` 作为模板。

```bash
export DATABASE_URL=sqlite:///./etf_momentum.db
```

Docker 部署时使用 named volume 持久化（路径 `/app/data/etf_momentum.db`），详见根 `README.md`。

## 数据库迁移

```bash
# 首次应用迁移
uv run alembic upgrade head

# 修改 model 后生成新迁移
uv run alembic revision --autogenerate -m "describe change"

# 降级一步
uv run alembic downgrade -1

# 查看当前版本
uv run alembic current
```

迁移文件位于 `backend/alembic/versions/`。

## 启动开发服务器

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- `GET /health` — 健康检查
- `GET /api/v1/etfs/count` — ETF 总数（冒烟端点，验证 DB 连接）
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc

## 运行测试

```bash
# 全部测试
uv run pytest

# 收集测试数（用于文档自检）
uv run pytest --collect-only -q | tail -1

# 单文件 / 单用例
uv run pytest tests/test_engine.py -v
uv run pytest -k "TestValidateParams" -v
```

测试使用内存 SQLite（`sqlite:///:memory:` + StaticPool），不依赖真实数据库文件。**截至 v1.0 共 267 个测试**（以 `pytest --collect-only -q` 当前输出为准）。

## 数据模型

| 表 | 用途 |
|---|---|
| `etfs` | ETF 主数据（code, name, market, category） |
| `daily_prices` | 日线 OHLCV 行情（UNIQUE(code, date)） |
| `backtest_runs` | 回测运行记录（参数 + 业绩 JSON + NAV 序列 JSON，含 sortino/calmar） |
| `signal_snapshots` | 每日动量信号（UNIQUE(date, etf_code)，score/rank 可空） |

价格字段使用 `Numeric(10, 4)`，避免浮点误差；成交量使用 `BigInteger`。

## CLI 命令

后端提供 2 组 CLI：数据同步 + 信号计算。所有命令通过 `uv run python -m app.<module> ...` 调用。

### 数据同步（akshare）

```bash
# 同步全市场 ETF 主数据到 etfs 表
uv run python -m app.data.sync etfs

# 同步指定 ETF 的日线行情（增量模式：从 DB 最后日期+1 到今天）
uv run python -m app.data.sync prices --codes 510300,510500

# 显式指定日期区间
uv run python -m app.data.sync prices --codes 510300 \
    --start 2024-01-01 --end 2024-12-31

# 全量拉取（从 akshare 起点 2000-01-01 到今天）
uv run python -m app.data.sync prices --codes 510300 --full
```

实现采用 Protocol 抽象（`AkshareClient`），sync 函数只依赖接口。运行时注入 `AkshareHttpClient`，测试注入 `FakeAkshareClient`，无需网络。

Upsert 通过 SQLite `INSERT ... ON CONFLICT DO UPDATE` 实现，重复运行同步相同区间不会抛错。CLI 退出码：0 全部成功 / 1 部分失败 / 2 全部失败。

### 信号计算

```bash
# 计算并落库
uv run python -m app.data.signal run --date 2024-12-31 --pool 510300,510500,510880

# 指定 top-N
uv run python -m app.data.signal run --date 2024-12-31 --pool 510300,510500 --top-n 2

# 覆盖已存在的快照
uv run python -m app.data.signal run --date 2024-12-31 --pool 510300 --force

# 查询
uv run python -m app.data.signal show --date 2024-12-31
```

CLI 内部从 `daily_prices` 表读历史，需要先用 `python -m app.data.sync prices` 同步数据。

### 演示数据灌入

> ⚠️ **演示数据仅用于系统功能演示，不构成投资建议**。

```bash
# 灌入内置演示数据集（15 只 ETF × ~1079 天 + 1 个 signal snapshot + 1 个示例 pool）
uv run python -m app.data.seed_demo

# 输出示例：
# loaded: etfs=15 daily_prices=16185 signals=15 pool=宽基三杰

# 指定其他 fixture 文件
uv run python -m app.data.seed_demo --fixture /path/to/other.json
```

**幂等**：重复执行 exit 0，DB 行数无增长（基于 upsert）。**离线可用**：不发起任何网络请求，只读本地 JSON。

**演示数据集内容**：
- 10 只宽基（沪深300/中证500/创业板/科创50/红利/上证50/深100/华夏300/上证180/深红利）
- 5 只行业（半导体/医疗/酒/消费/黄金）
- 时间窗口：最近 ~1079 个交易日（约 3 年），截至 fixture `generated_at` 字段
- 1 个 signal snapshot：top-5 = BUY，其余 10 只 = HOLD
- 1 个示例 pool「宽基三杰」：510300/510500/159915

**演示数据生成器**（开发者手动工具，不入 CI / 不入容器镜像）：

```bash
# 在 backend 目录下重新拉取最新 akshare 数据生成 fixture
uv run python -m app.data.seed_demo_generator --lookback-days 750
```

> 该命令依赖网络（akshare），且每次生成结果略有差异。仅在维护者需要刷新 fixture 时手动跑。

## 动量因子

12-1 动量（classic AQR / Carhart 定义）：衡量过去 12 个月收益、跳过最近 1 个月，避免短期反转效应。

### 公式

```
momentum(t) = close(t - skip - 1) / close(t - skip - 1 - lookback) - 1
```

默认参数 `lookback=252`（约 12 个月交易日）+ `skip=21`（约 1 个月 skip）。

### 模块位置

```
app/factors/
├── __init__.py             # re-export 三个公开函数
└── momentum.py             # compute_momentum_score / compute_momentum_scores / rank_scores
```

### API 用法

```python
from decimal import Decimal
from app.factors import (
    compute_momentum_score,
    compute_momentum_scores,
    rank_scores,
)

# 1) 单只 ETF
closes = [Decimal("1.00")] * 280
closes[-22] = Decimal("1.20")   # 12-1 窗口末端
closes[-274] = Decimal("1.00")  # 12-1 窗口起点
score = compute_momentum_score(closes)
# → Decimal("0.20")

# 2) 批量 ETF
price_history = {
    "510300": closes_300,
    "510500": closes_500,
}
scores = compute_momentum_scores(price_history)
# → {"510300": Decimal("0.20"), "510500": None}  （数据不足 → None）

# 3) 排名（UI 消费）
ranked = rank_scores(scores)
# → [("510300", 1, Decimal("0.20")), ("510500", None, None)]
```

### 设计决策

| 决策 | 行为 | 说明 |
|------|------|------|
| 同分排名 | 并列同名次（competition ranking），跳号赋名次 | `[1, 1, 3]` 风格；同分时按输入 dict 插入顺序（Python `sorted` 稳定） |
| None 分数 | 保留在列表末尾，`rank=None`，不占名次槽 | UI 一目了然哪些 ETF 无数据；调用方遍历友好 |
| Decimal 精度 | **不 quantize**，保留完整精度 | 调用方在写入 DB 时再 `quantize(Decimal('0.0001'))` |
| 异常价格 | `close <= 0` 视为脏数据 → 返回 None | 与数据不足同等处理，纯函数不抛异常中断批量计算 |
| 范围 | 仅做动量单因子 | 多因子合成、行业中性化等不在本模块范围 |

## 回测引擎

把「动量因子 + 调仓规则 + 净值跟踪」串成端到端流程。`run_backtest` 是纯函数（不读 DB），`save_backtest_run` 单独负责持久化。

### 模块位置

```
app/backtest/
├── __init__.py             # re-export BacktestParams / run_backtest / save_backtest_run / compute_metrics
├── engine.py               # 纯计算：run_backtest + BacktestParams + RebalanceEvent + BacktestResult
├── metrics.py              # 纯计算：compute_metrics（6 个指标）
└── persistence.py          # save_backtest_run：写 BacktestRun ORM 行
```

### 参数 `BacktestParams`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `etf_pool` | `list[str]` | — | ETF 代码池 |
| `start` | `date` | — | 回测起始日 |
| `end` | `date` | — | 回测结束日 |
| `initial_cash` | `Decimal` | — | 初始资金 |
| `lookback` | `int` | 252 | 动量回望窗口（交易日） |
| `skip` | `int` | 21 | 动量 skip（交易日） |
| `top_n` | `int` | 5 | 每月/季选 top-N |
| `rebalance_freq` | `RebalanceFrequency` | MONTHLY | 调仓频率：`MONTHLY` / `QUARTERLY` |

### API 用法

```python
from datetime import date
from decimal import Decimal
from app.backtest import (
    BacktestParams,
    RebalanceFrequency,
    run_backtest,
    save_backtest_run,
)
from app.db.session import SessionLocal

# 1) 准备价格历史（通常从 DailyPrice 表读出后转成此格式）
price_history: dict[str, list[tuple[date, Decimal]]] = {
    "510300": [(date(2024, 1, 2), Decimal("3.85")), ...],
    "510500": [...],
}

# 2) 构造参数
params = BacktestParams(
    etf_pool=["510300", "510500"],
    start=date(2024, 1, 1),
    end=date(2024, 12, 31),
    initial_cash=Decimal("100000"),
    top_n=2,
    rebalance_freq=RebalanceFrequency.MONTHLY,
)

# 3) 运行回测（纯函数，无 DB）
result = run_backtest(params, price_history)
print(result.metrics)
# → {'total_return': Decimal('0.20'), 'annualized_return': Decimal('0.20'),
#    'max_drawdown': Decimal('0.05'), 'sharpe_ratio': Decimal('1.5'),
#    'sortino_ratio': Decimal('2.1'), 'calmar_ratio': Decimal('4.0')}

# 4) 持久化（metrics 中 sortino/calmar 一并写入）
with SessionLocal() as session:
    run = save_backtest_run(session, params, result)
```

### 设计决策

| 决策 | 行为 | 说明 |
|------|------|------|
| 权重 | **等权**（每个入选 ETF 拿 1/top_n 资金） | 学术标准、AQR 默认；不足 top_n 时按比例摊分剩余 |
| 调仓日 | `MONTHLY` = 该月最后一个交易日；`QUARTERLY` = 3/6/9/12 月最后交易日 | A 股业界惯例 |
| 退市 ETF | 最后有数据的一日按 close 卖出，转为现金 | NAV 保持连续，避免估值冻结 |
| 净值跟踪 | **每日跟踪**，用每日 close 重估持仓 | max_drawdown 准确，UI 曲线完整 |
| 计算与持久化分离 | `run_backtest` 纯函数；`save_backtest_run` 写 ORM | 单测只测计算逻辑；持久化 mock session |
| Decimal 精度 | 净值 / 权重 全程 Decimal；sharpe 用 `Decimal.sqrt()`（Py 3.11+） | 与 DailyPrice.Numeric(10,4) 同族 |
| 摩擦建模 | **无** 手续费 / 滑点 / 印花税 / 分红再投资 | MVP 简化；后续可加 fee/slippage 参数 |

## 业绩指标

`app.backtest.metrics.compute_metrics` 是纯函数，接收净值序列返回 6 个业绩指标。可独立 import（不依赖 engine / DB）。

### 6 个指标

| 指标 | 公式 | 边界处理 |
|------|------|---------|
| `total_return` | `(final_nav / initial_cash) - 1` | 空序列 → `Decimal("0")` |
| `annualized_return` | `(final / initial) ** (365 / days) - 1`，`days = (last - first).days` | `days <= 0` 或非正净值 → `Decimal("0")` |
| `max_drawdown` | `max over t of (peak(t) / nav(t) - 1)`，`peak(t) = max(nav[0..t])` | 空序列 → `Decimal("0")` |
| `sharpe_ratio` | `mean(excess) / std(all_returns) * sqrt(252)`，`excess = r - risk_free_rate / 252` | std = 0 或 `< 2 returns` → `None` |
| `sortino_ratio` | `mean(excess) / std(negative_returns) * sqrt(252)`（仅下行波动） | 无负收益或 `< 2 returns` → `None` |
| `calmar_ratio` | `annualized_return / max_drawdown` | `max_drawdown == 0` → `None` |

**年化因子**：`sqrt(252)`，与 AQR / Carhart 等学术文献一致（标准 1 年交易日数）。
**日收益**：`nav[i] / nav[i-1] - 1`，从 i = 1 开始。

### 调用示例

```python
from datetime import date
from decimal import Decimal
from app.backtest import compute_metrics

nav_series = [
    (date(2024, 1, 1),  Decimal("100")),
    (date(2024, 6, 30), Decimal("110")),
    (date(2024, 12, 31), Decimal("120")),
]
metrics = compute_metrics(nav_series, Decimal("100"))
# {
#   "total_return":       Decimal("0.2"),
#   "annualized_return":  Decimal("0.2"),
#   "max_drawdown":       Decimal("0"),
#   "sharpe_ratio":       ...,
#   "sortino_ratio":      ...,
#   "calmar_ratio":       ...,
# }

# 显式传无风险利率（年化）
metrics = compute_metrics(
    nav_series,
    Decimal("100"),
    risk_free_rate=Decimal("0.02"),  # 2% 年化
)
```

### 边界行为速查

| 输入 | 行为 |
|------|------|
| `nav_series = []` | 全部 0 / None（ratios 全部 None） |
| 单点 | `total_return = 0`，所有 ratios = None |
| 常数 NAV（无波动） | `sharpe_ratio` / `sortino_ratio` = None（std = 0） |
| 全部正收益 | `sortino_ratio` = None（无下行波动） |
| 单点负收益 | `sortino_ratio` = None（std 自由度不足） |
| 单调递增 NAV | `max_drawdown = 0`，`calmar_ratio` = None |
| 净值下跌 | `calmar_ratio` 为负数（允许） |

### 与回测引擎的关系

`app/backtest/engine.py:run_backtest` 内部直接调用 `compute_metrics(nav_series, params.initial_cash)`，不再内嵌计算逻辑。如需在调用方拿到完整的 6 个指标（含 sortino / calmar），直接读 `BacktestResult.metrics` 即可。

## 实时信号

`app.signals.compute.compute_signals` + `app.signals.persistence.save_signal_snapshot` 把「今日 ETF 动量排名 + 调仓建议」算出并落到 `signal_snapshots` 表，供前端看板按日查询。可独立 import（不依赖 backtest / DB driver）。

### SignalRow 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `etf_code` | `str` | ETF 代码 |
| `momentum_score` | `Decimal \| None` | 12-1 动量；quantize 到 6 位；WATCH 时为 None |
| `rank` | `int \| None` | competition ranking（1, 1, 3 跳号）；WATCH 时为 None |
| `action` | `str` | `BUY` / `HOLD` / `WATCH` 三态之一 |

### Action 语义

| Action | 条件 | 含义 |
|--------|------|------|
| `BUY` | `rank ≤ top_n` 且 score 非 None | 调仓日应该买入 |
| `HOLD` | score 非 None 但 `rank > top_n` | 暂不调仓，继续持有 |
| `WATCH` | score = None | 价格历史不足（< 273 个交易日），建议观望 |

> SELL 信号（昨日 BUY 集合 − 今日 BUY 集合）由前端对比两日快照得出，不写入 action 字段。

### 调用示例

```python
from datetime import date
from decimal import Decimal
from app.signals import compute_signals, save_signal_snapshot

price_history = {
    "510300": [(date(2024, 1, 2), Decimal("4.100")), ...],   # 至少 273 个 close
    "510500": [(date(2024, 1, 2), Decimal("2.300")), ...],
}
rows = compute_signals(
    ["510300", "510500"],
    price_history,
    date(2024, 12, 31),
    top_n=2,
)
# [
#   SignalRow(etf_code="510300", momentum_score=Decimal("0.234567"), rank=1, action="BUY"),
#   SignalRow(etf_code="510500", momentum_score=Decimal("0.100000"), rank=2, action="HOLD"),
# ]
```

### 持久化

```python
from app.signals import save_signal_snapshot
from app.db.session import SessionLocal

session = SessionLocal()
try:
    written = save_signal_snapshot(session, date(2024, 12, 31), rows)
    # overwrite=True 时覆盖同 (date, etf_code) 已存在行
finally:
    session.close()
```

### 边界行为速查

| 输入 | 行为 |
|------|------|
| `etf_pool=[]` | 返回 `[]`；save 写 0 行 |
| 价格历史 < 273 天 | 该 ETF → `WATCH`，score/rank=None，仍落库 |
| pool 包含 DB 不存在的 code | WATCH 落库（不抛错） |
| 同 (date, etf_code) 已存在 | `overwrite=False` 跳过；`overwrite=True` 更新 |
| `top_n=0` 或负数 | `ValueError` |
| `top_n > len(pool)` | 全部 BUY |

## REST API

`app/api/v1/` 暴露 5 个 router，共 17 个业务端点（外加 `/health` = 18 总数）。**完整 schema 与请求/响应示例以 Swagger UI（`http://localhost:8000/docs`）为准**——本表为速查。

### 端点速查表（17 业务端点 + 1 health = 18 总）

| 方法 | 路径 | 用途 | 关键参数 |
|------|------|------|---------|
| GET | `/health` | 健康检查 | — |
| GET | `/api/v1/etfs` | ETF 列表（分页 + category 过滤） | `?limit=50&offset=0&category=...` |
| GET | `/api/v1/etfs/count` | ETF 总数（冒烟） | — |
| GET | `/api/v1/etfs/{code}` | ETF 详情 | — |
| GET | `/api/v1/etfs/{code}/prices` | 日线历史（升序） | `?start=YYYY-MM-DD&end=YYYY-MM-DD&limit=500` |
| GET | `/api/v1/pools` | ETF 策略池列表 | — |
| POST | `/api/v1/pools` | 创建策略池 | body: `{name, etf_codes: [...]}` |
| GET | `/api/v1/pools/{pool_id}` | 策略池详情 | — |
| PUT | `/api/v1/pools/{pool_id}` | 更新策略池 | body: `{name?, etf_codes?}` |
| DELETE | `/api/v1/pools/{pool_id}` | 删除策略池 | — |
| GET | `/api/v1/signals?date=...` | 指定日期 snapshot | 不传 date → 最新 |
| GET | `/api/v1/signals/latest` | 显式 latest | — |
| POST | `/api/v1/backtest` | 提交新回测（同步执行） | body: `{etf_pool, start, end, initial_cash, ...}` |
| GET | `/api/v1/backtest` | BacktestRun 列表（按 created_at desc） | `?limit=20&offset=0` |
| GET | `/api/v1/backtest/{run_id}` | BacktestRun 详情（含 metrics） | — |
| GET | `/api/v1/backtest/{run_id}/nav` | NAV 序列 | — |
| POST | `/api/v1/sync/etfs` | 触发 ETF 主数据同步 | — |
| POST | `/api/v1/sync/prices` | 触发日线同步 | body: `{codes, start?, end?, full?}` |

### 关键约定

| 项 | 约定 |
|----|------|
| 分页 | `limit` 默认 50，clamp 到 [1, 500]；`offset` 默认 0，clamp 到 ≥ 0 |
| Decimal 序列化 | 所有 Decimal 字段（价格、动量、metrics）以 `string` 返回，前端用 `parseFloat` |
| 错误格式 | FastAPI 默认 `{detail: "..."}`；404 / 422 自动产生 |
| CORS | `allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]`（Vite dev） |
| 日期格式 | ISO 8601 `YYYY-MM-DD` / `YYYY-MM-DDTHH:MM:SS+00:00` |
| 写操作 | `POST /backtest`、`POST /sync/*`、`POST/PUT/DELETE /pools`；其余只读 |

### curl 示例

```bash
# 1) 列出前 10 只 ETF
curl -s "http://localhost:8000/api/v1/etfs?limit=10" | jq .

# 2) 提交一次回测（同步执行 → 返回完整 BacktestRun JSON）
curl -s -X POST http://localhost:8000/api/v1/backtest \
    -H "Content-Type: application/json" \
    -d '{
      "etf_pool": ["510300", "510500", "511010"],
      "start": "2024-04-01",
      "end": "2024-09-30",
      "initial_cash": "100000",
      "lookback": 60,
      "skip": 5,
      "top_n": 2,
      "rebalance_freq": "monthly"
    }' | jq .

# 3) 拿最新信号
curl -s "http://localhost:8000/api/v1/signals/latest" | jq .

# 4) 同步 ETF 主数据
curl -s -X POST http://localhost:8000/api/v1/sync/etfs | jq .

# 5) 创建策略池
curl -s -X POST http://localhost:8000/api/v1/pools \
    -H "Content-Type: application/json" \
    -d '{"name":"宽基三杰","etf_codes":["510300","510500","159915"]}' | jq .
```

### 错误格式

FastAPI 默认错误响应：

```json
// 404
{ "detail": "ETF 999999 not found" }

// 422（Pydantic 校验）
{
  "detail": [
    {
      "type": "too_short",
      "loc": ["body", "etf_pool"],
      "msg": "List should have at least 1 item after validation, not 0",
      "input": []
    }
  ]
}

// 422（业务校验：数据不足）
{ "detail": "insufficient price history for: ['511010']. POST /api/v1/sync/prices first." }
```

### 设计决策

| 决策 | 行为 | 说明 |
|------|------|------|
| 路径前缀 | `/api/v1` | 与已有 `api_v1_router` 对齐；未来 v2 不影响 v1 客户端 |
| 同步 vs 异步 | `POST /backtest` 同步执行（最长约 10 秒） | MVP 单用户本地部署；不引入任务队列 |
| 分页 | `?limit=N&offset=M` | 1k 级别 ETF 足够；不引入 cursor |
| Decimal | 序列化为 `string` | 金融保精度；前端 `parseFloat` 后 `toFixed` 还原 |
| CORS | `localhost:5173` + `127.0.0.1:5173` | 满足本地 dev + Docker compose |
| 错误格式 | FastAPI 默认 `{detail: ...}` | 0 额外实现；OpenAPI 原生支持 |
| 写操作 | `/backtest` `/sync/*` `/pools` POST/PUT/DELETE | ETF 数据由 akshare 同步，API 不提供 etfs 增删改 |
| 复用 | router 直接调 `app.backtest` / `app.signals` / `app.data` | 不重新实现业务逻辑 |
| 测试 | FastAPI `TestClient` + 内存 SQLite | 端到端 HTTP 行为验证 |

## Docker

详见根目录 `README.md` 的「Docker Compose」章节。本目录下：

- `Dockerfile`：基于 `python:3.11-slim` + uv，`uvicorn --reload` 启动
- `.dockerignore`：排除 `.venv`、`__pycache__`、`*.db` 等

容器内 CLI：

```bash
# 在 backend 容器内运行
docker compose exec backend uv run python -m app.data.sync etfs
docker compose exec backend uv run python -m app.data.sync prices --codes 510300
docker compose exec backend uv run python -m app.data.signal run --date 2024-12-31 --pool 510300
```

## 项目结构

```
backend/
├── app/
│   ├── core/config.py           # DATABASE_URL 配置
│   ├── db/
│   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   └── session.py           # engine + SessionLocal + get_db
│   ├── models/                  # 4 个 ORM model
│   │   ├── etf.py
│   │   ├── daily_price.py
│   │   ├── backtest_run.py
│   │   └── signal_snapshot.py
│   ├── repositories/
│   │   └── etf_repository.py    # EtfRepository
│   ├── data/                    # akshare 数据同步 + signal CLI + 演示数据
│   │   ├── client.py            # AkshareClient Protocol + AkshareHttpClient + FakeAkshareClient
│   │   ├── upsert.py            # upsert_etf / upsert_daily_price
│   │   ├── etf_master.py        # sync_etf_master
│   │   ├── daily_prices.py      # sync_daily_prices
│   │   ├── sync.py              # sync CLI 入口
│   │   ├── signal.py            # signal CLI 入口（run / show）
│   │   ├── seed_demo.py         # 演示数据 loader CLI（灌入 demo_data.json）
│   │   ├── seed_demo_generator.py # 演示数据 generator（开发者手动工具，不入 CI）
│   │   └── fixtures/            # 内置演示数据
│   │       └── demo_data.json   # akshare 一次性快照（≈2.7 MB）
│   ├── factors/                 # 因子计算原语
│   │   └── momentum.py          # 12-1 动量
│   ├── backtest/                # 回测引擎
│   │   ├── engine.py            # run_backtest + BacktestParams + BacktestResult
│   │   ├── metrics.py           # 6 指标 compute_metrics
│   │   └── persistence.py       # save_backtest_run（含 sortino/calmar 写入）
│   ├── signals/                 # 实时信号计算 + 持久化
│   │   ├── compute.py           # compute_signals + SignalRow
│   │   └── persistence.py       # save_signal_snapshot
│   ├── api/
│   │   ├── health.py            # GET /health
│   │   └── v1/
│   │       ├── router.py        # 聚合 5 个 router
│   │       ├── schemas.py       # Pydantic 请求/响应模型
│   │       ├── etfs.py          # /api/v1/etfs 4 个端点
│   │       ├── pools.py         # /api/v1/pools 5 个端点
│   │       ├── signals.py       # /api/v1/signals 2 个端点
│   │       ├── backtest.py      # /api/v1/backtest 4 个端点
│   │       └── sync.py          # /api/v1/sync 2 个端点
│   └── main.py                  # FastAPI app + CORS + router 挂载
├── tests/                       # 267 个 pytest 测试
│   ├── conftest.py              # 共享 fixtures
│   ├── test_*.py                # 17 个测试文件
├── alembic/                     # 迁移
│   ├── env.py
│   ├── versions/8c872b9f6bda_initial_schema.py
│   ├── versions/a1b2c3d4e5f6_signal_snapshot_nullable_score_rank.py
│   └── versions/b1c2d3e4f5a6_backtest_run_nav_series.py
├── pyproject.toml
├── uv.lock
└── README.md
```

**测试覆盖**：截至 v1.0 共 **267 个测试**（含动量 / 回测 / 指标 / 信号 / REST API / CLI / Schema / CORS）。自检命令：`uv run pytest --collect-only -q | tail -1`。

## 后续计划

> v1.0 范围已全部交付（参见根 `README.md` 里程碑章节）。本节仅列 v2.0+ 占位项。

- **v2.0**：
  - 多策略对比（双动量、相对动量、行业中性化）
  - 美股 ETF 扩展（数据源候选：yfinance / polygon）
  - 用户账户与策略持久化（多用户）
  - 实时告警（邮件 / 微信）
  - 任务调度（每日数据自动同步，可选 APScheduler）
  - 实盘交易接入（券商 API）
  - 摩擦建模（手续费 / 滑点 / 印花税 / 分红再投资）
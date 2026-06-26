# etf-momentum Backend

A 股 ETF 动量策略系统的后端服务。基于 FastAPI + SQLAlchemy 2.0 + Alembic，使用 `uv` 管理依赖。

## 项目简介

本目录是 etf-momentum 项目的后端实现。当前阶段提供：

- FastAPI 应用入口（`app/main.py`）
- 健康检查端点 `GET /health`
- 业务路由前缀 `/api/v1`（含冒烟端点 `GET /api/v1/etfs/count`）
- SQLite 数据层：4 个核心实体（ETF / DailyPrice / BacktestRun / SignalSnapshot）
- Alembic 数据库迁移
- Repository 模式（`EtfRepository`）演示查询封装
- Session 通过 FastAPI `Depends(get_db)` 注入
- akshare 数据同步（CLI：`python -m app.data.sync`）
- 动量因子计算原语（`app/factors/momentum`）—— 12-1 动量纯函数模块
- 自动化测试覆盖（`pytest` + 内存 SQLite）

后续将在此基础上添加回测引擎、信号计算持久化、REST API 等业务模块。

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
uv run pytest
```

测试使用内存 SQLite（`sqlite:///:memory:` + StaticPool），不依赖真实数据库文件。

## 数据模型

| 表 | 用途 |
|---|---|
| `etfs` | ETF 主数据（code, name, market, category） |
| `daily_prices` | 日线 OHLCV 行情（UNIQUE(code, date)） |
| `backtest_runs` | 回测运行记录（参数 + 业绩 JSON） |
| `signal_snapshots` | 每日动量信号（UNIQUE(date, etf_code)） |

价格字段使用 `Numeric(10, 4)`，避免浮点误差；成交量使用 `BigInteger`。

## 数据同步（akshare）

CLI 入口：`python -m app.data.sync`

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
| 范围 | **不写** `signal_snapshots` | 持久化由后续「实时信号计算与排名」change 负责 |
| 范围 | 仅做动量单因子 | 多因子合成、行业中性化等不在本模块范围 |

## Docker

详见根目录 `README.md` 的「Docker Compose」章节。本目录下：

- `Dockerfile`：基于 `python:3.11-slim` + uv，`uvicorn --reload` 启动
- `.dockerignore`：排除 `.venv`、`__pycache__`、`*.db` 等

容器内 CLI：

```bash
# 在 backend 容器内运行
docker compose exec backend uv run python -m app.data.sync etfs
docker compose exec backend uv run python -m app.data.sync prices --codes 510300
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
│   ├── data/                    # akshare 数据同步
│   │   ├── client.py            # AkshareClient Protocol + AkshareHttpClient + FakeAkshareClient
│   │   ├── upsert.py            # upsert_etf / upsert_daily_price
│   │   ├── etf_master.py        # sync_etf_master
│   │   ├── daily_prices.py      # sync_daily_prices
│   │   └── sync.py              # CLI 入口
│   ├── factors/                 # 因子计算原语
│   │   └── momentum.py          # 12-1 动量
│   ├── api/
│   │   ├── health.py
│   │   └── v1/
│   │       ├── etfs.py          # /api/v1/etfs/count
│   │       └── router.py
│   └── main.py
├── tests/                       # 68 个测试覆盖（21 数据模型 + 20 akshare sync + 27 动量因子）
├── alembic/                     # 迁移
│   ├── env.py
│   └── versions/8c872b9f6bda_initial_schema.py
├── pyproject.toml
├── uv.lock
└── README.md
```

## 后续计划

- 回测引擎（参数化：ETF 池、动量窗口、调仓频率）
- 业绩指标计算（年化收益、最大回撤、夏普）
- 实时信号计算与排名（写入 `signal_snapshots`）
- 业务 API：`/api/etfs` / `/api/signals` / `/api/backtest`
- 任务调度（每日数据更新）

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
- 自动化测试覆盖（`pytest` + 内存 SQLite）

后续将在此基础上添加数据同步、回测引擎、信号计算等业务模块。

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
│   ├── api/
│   │   ├── health.py
│   │   └── v1/
│   │       ├── etfs.py          # /api/v1/etfs/count
│   │       └── router.py
│   └── main.py
├── tests/                       # 21 个测试覆盖
├── alembic/                     # 迁移
│   ├── env.py
│   └── versions/0001_initial.py
├── pyproject.toml
├── uv.lock
└── README.md
```

## 后续计划

- akshare / baostock 数据同步脚本
- 业务 API：ETF 池管理、回测、信号
- 动量因子计算与回测引擎
- 任务调度（每日数据更新）

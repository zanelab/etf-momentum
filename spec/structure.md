# 项目目录结构说明

## 架构选择
全栈（后端 + 前端 Web）— 2026-06-26 初始化时确认

## 后端实现状态（2026-06-26 更新）
FastAPI 脚手架 + SQLite 数据模型 + akshare 数据同步 + 12-1 动量因子 + 回测引擎 + 业绩指标模块 + 实时信号计算 + 12 端点 REST API + CORS 已就位（change: backend-fastapi-scaffold、sqlite-data-model、akshare-data-sync、momentum-factor、backtest-engine、metrics-extraction、realtime-signals、rest-api，已归档）。

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口 + CORSMiddleware + lifespan 打印 DATABASE_URL
│   ├── core/
│   │   └── config.py           # DATABASE_URL 配置
│   ├── db/
│   │   ├── base.py             # SQLAlchemy DeclarativeBase
│   │   └── session.py          # engine + SessionLocal + get_db (Depends)
│   ├── models/                 # 4 个 ORM model（BacktestRun 含 nav_series JSON）
│   │   ├── etf.py
│   │   ├── daily_price.py
│   │   ├── backtest_run.py
│   │   └── signal_snapshot.py
│   ├── repositories/
│   │   └── etf_repository.py   # EtfRepository
│   ├── data/                   # akshare 数据同步
│   │   ├── client.py           # AkshareClient Protocol + Http + Fake
│   │   ├── etf_master.py       # sync_etf_master
│   │   ├── daily_prices.py     # sync_daily_prices
│   │   ├── upsert.py           # upsert_etf / upsert_daily_price
│   │   ├── signal.py           # python -m app.data.signal run|show
│   │   └── sync.py             # CLI 入口 (python -m app.data.sync)
│   ├── factors/                # 因子计算原语（纯函数）
│   │   └── momentum.py         # 12-1 动量
│   ├── backtest/               # 回测引擎
│   │   ├── engine.py           # run_backtest + BacktestParams + RebalanceEvent + BacktestResult
│   │   ├── metrics.py          # 6 个业绩指标纯函数
│   │   └── persistence.py      # save_backtest_run (含 nav_series)
│   ├── signals/                # 实时信号计算
│   │   ├── compute.py          # compute_signals + SignalRow
│   │   └── persistence.py      # save_signal_snapshot
│   └── api/
│       ├── health.py           # GET /health
│       └── v1/
│           ├── router.py       # 聚合 4 个 router (/api/v1 前缀)
│           ├── schemas.py      # 13 个 Pydantic 模型（Decimal → str）
│           ├── etfs.py         # /api/v1/etfs 4 个端点
│           ├── signals.py      # /api/v1/signals 2 个端点
│           ├── backtest.py     # /api/v1/backtest 4 个端点
│           └── sync.py         # /api/v1/sync 2 个端点
├── tests/                      # 200 个 pytest 用例（146 原有 + 54 API）
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_etf.py
│   ├── test_daily_price.py
│   ├── test_backtest_run.py
│   ├── test_backtest_engine.py
│   ├── test_backtest_metrics.py
│   ├── test_backtest_persistence.py
│   ├── test_signal_snapshot.py
│   ├── test_signal_cli.py
│   ├── test_signals_compute.py
│   ├── test_signals_persistence.py
│   ├── test_session.py
│   ├── test_config.py
│   ├── test_etfs_api.py
│   ├── test_api_schemas.py
│   ├── test_api_etfs.py
│   ├── test_api_signals.py
│   ├── test_api_backtest.py
│   ├── test_api_sync.py
│   ├── test_api_cors.py
│   ├── test_akshare_client.py
│   ├── test_upsert.py
│   ├── test_etf_master_sync.py
│   ├── test_daily_prices_sync.py
│   ├── test_sync_cli.py
│   └── test_momentum.py
├── alembic/                    # 迁移目录
│   ├── env.py
│   ├── versions/8c872b9f6bda_initial_schema.py
│   ├── versions/a1b2c3d4e5f6_signal_snapshot_nullable_score_rank.py
│   └── versions/b1c2d3e4f5a6_backtest_run_nav_series.py
├── alembic.ini
├── .env.example
├── pyproject.toml              # uv 依赖管理
├── uv.lock
└── README.md
```

## 前端实现状态（2026-06-26）
Vite + React + TypeScript 脚手架已就位（change: frontend-vite-react-scaffold，已归档）。

```
frontend/
├── public/
├── src/
│   ├── __tests__/              # Vitest 测试
│   │   ├── cn.test.ts
│   │   ├── health-store.test.ts
│   │   └── setup.ts
│   ├── api/client.ts           # fetch 封装 + ApiError
│   ├── components/ui/button.tsx # shadcn Button
│   ├── layouts/Layout.tsx      # 左侧导航 + 顶部标题 + Outlet
│   ├── lib/utils.ts            # cn() 工具
│   ├── pages/HealthPage.tsx    # /health 页面
│   ├── stores/health-store.ts  # Zustand 健康检查状态
│   ├── App.tsx                 # 路由配置
│   ├── main.tsx                # React 入口
│   ├── index.css               # Tailwind + shadcn CSS 变量
│   └── vite-env.d.ts
├── index.html
├── vite.config.ts              # Vite + Vitest
├── tsconfig.json               # TS strict
├── tsconfig.node.json
├── tailwind.config.js
├── postcss.config.js
├── package.json
├── pnpm-lock.yaml
└── README.md
```

## 目录布局

```
etf-momentum/
├── spec/                     # 项目级 Spec
│   ├── requirements.md       # 整体需求
│   ├── design.md             # 架构设计
│   ├── tasks.md              # 里程碑任务
│   ├── devlog.md             # 开发日志
│   └── structure.md          # 本文档
├── openspec/                 # OpenSpec 配置
│   ├── config.yaml           # OpenSpec 配置（schema: spec-driven）
│   ├── specs/                # 长期规格
│   └── changes/
│       └── archive/          # 已归档变更
├── backend/                  # 后端代码（FastAPI + SQLAlchemy + Alembic + akshare）
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/                 # 前端代码（Vite + React + TS）
│   ├── Dockerfile
│   ├── .dockerignore
│   └── .npmrc
├── scripts/
│   └── verify-docker.sh      # Docker 冒烟脚本
├── docker-compose.yml        # 一键启动 backend + frontend
├── Makefile                  # docker compose 便捷命令
├── README.md                 # 根 README（含 Docker 启动章节）
└── AGENTS.md                 # 开发规则
```

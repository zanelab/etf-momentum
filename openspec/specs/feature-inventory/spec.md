## ADDED Requirements

### Requirement: README 提供 v1.0 功能特性的速查结构

README MUST 采用以下章节结构（顺序可调整但章节齐备），让新用户在 2 分钟内了解系统能力。

#### Scenario: 章节齐备
- **WHEN** 用户阅读根 README
- **THEN** MUST 包含以下章节：(1) 项目简介（一段话）(2) 快速开始（端到端首跑）(3) 功能特性（5 项业务能力清单）(4) 项目结构（顶层目录）(5) Docker 常用命令 / 本地开发命令 (6) 故障排查（≥3 类）(7) 文档导航（指向子 README + spec/）(8) 里程碑（指向 `spec/tasks.md`）

#### Scenario: 每个特性章节给出代码定位
- **WHEN** 「功能特性」章节列出能力
- **THEN** 每项 MUST 附上对应代码路径或 API 路径（让想深入的用户有入口）

### Requirement: backend/README 提供 API 端点速查表

`backend/README.md` MUST 包含一张「API 端点速查表」，列出全部 12 个端点，并指向 Swagger UI 作为权威 schema 来源。

#### Scenario: API 表覆盖全部 18 个端点
- **WHEN** 用户查阅 API 表
- **THEN** 表中 MUST 列出以下 18 个端点（方法 + 路径 + 一行说明）：
  - `GET /health`
  - `GET /api/v1/etfs`
  - `GET /api/v1/etfs/count`
  - `GET /api/v1/etfs/{code}`
  - `GET /api/v1/etfs/{code}/prices`
  - `GET /api/v1/pools`
  - `POST /api/v1/pools`
  - `GET /api/v1/pools/{pool_id}`
  - `PUT /api/v1/pools/{pool_id}`
  - `DELETE /api/v1/pools/{pool_id}`
  - `GET /api/v1/signals/latest`
  - `GET /api/v1/signals?date=YYYY-MM-DD`
  - `POST /api/v1/backtest`
  - `GET /api/v1/backtest`
  - `GET /api/v1/backtest/{run_id}`
  - `GET /api/v1/backtest/{run_id}/nav`
  - `POST /api/v1/sync/etfs`
  - `POST /api/v1/sync/prices`

#### Scenario: 指向 Swagger 作为权威来源
- **WHEN** API 表说明
- **THEN** MUST 注明「完整 schema 与请求/响应示例以 `http://localhost:8000/docs` Swagger UI 为准」，避免 README 漂移

### Requirement: backend/README 提供 CLI 命令清单

`backend/README.md` MUST 列出全部 CLI 命令及其典型用法。

#### Scenario: CLI 覆盖数据同步 + 信号
- **WHEN** 用户阅读 CLI 章节
- **THEN** MUST 涵盖：
  - `python -m app.data.sync etfs`
  - `python -m app.data.sync prices --codes <code1,code2> [--full] [--start YYYY-MM-DD --end YYYY-MM-DD]`
  - `python -m app.data.signal run --date YYYY-MM-DD --pool <codes>`
  - `python -m app.data.signal show --date YYYY-MM-DD`

#### Scenario: CLI 命令与代码一致
- **WHEN** CLI 章节列出命令
- **THEN** 参数 MUST 与 `app/data/sync.py` / `app/data/signal.py` argparse 定义完全一致（不多不少）

### Requirement: frontend/README 列出页面与 Zustand store

`frontend/README.md` MUST 给出 v1.0 全部页面与 Zustand store 的清单。

#### Scenario: 4 个页面 + Layout + 5 个 store
- **WHEN** 用户阅读「页面」章节
- **THEN** MUST 列出：
  - 页面：`/dashboard` (DashboardPage) / `/backtest` (BacktestPage) / `/pools` (PoolsPage) / `/health` (HealthPage)
  - Layout：`src/layouts/Layout.tsx`（左侧 NavLink + 顶部标题 + `<Outlet/>`）
  - Zustand store：`useHealthStore` / `useEtfsStore` / `useSignalsStore` / `useBacktestStore` / `usePoolsStore`

### Requirement: 项目结构图必须真实

README / backend/README / frontend/README 中所有 ASCII 树状结构 MUST 与仓库当前目录一致。

#### Scenario: 顶层目录树准确
- **WHEN** 根 README 列出顶层目录
- **THEN** MUST 包含：`backend/` `frontend/` `openspec/` `spec/` `scripts/` `docker-compose.yml` `Makefile` `README.md` `AGENTS.md`

#### Scenario: backend 目录树准确
- **WHEN** backend/README 列出子目录
- **THEN** MUST 包含：`app/{core,db,models,repositories,data,factors,backtest,signals,api/v1}` + `tests/` + `alembic/`

#### Scenario: frontend 目录树准确
- **WHEN** frontend/README 列出子目录
- **THEN** MUST 包含：`src/{api,components/ui,layouts,lib,pages,stores,__tests__}` + 顶层配置文件
## ADDED Requirements

### Requirement: 用户能在 5 分钟内从 clone 到看到 Dashboard 数据

README 的「快速开始」章节 MUST 给出端到端首跑流程，让用户在 5 分钟内完成以下全部步骤：

#### Scenario: 完整首跑流程
- **WHEN** 新用户按 README 的「快速开始」依次执行
- **THEN** 顺序完成：(1) `docker compose up -d` 启动容器 (2) `docker compose exec backend uv run alembic upgrade head` 创建表结构 (3) `docker compose exec backend uv run python -m app.data.sync etfs` 同步 ETF 主数据 (4) `docker compose exec backend uv run python -m app.data.sync prices --codes 510300,510500 --full` 同步若干标的的历史价格 (5) 浏览器打开 `http://localhost:5173/dashboard` 看到动量排名

#### Scenario: 命令与 Makefile 一致
- **WHEN** 章节列出命令
- **THEN** 优先使用 `make up` / `make logs` 等 Makefile 目标；非 Docker 场景再给出 `uv run` / `pnpm` 命令
- **AND** 列出的所有命令 MUST 在仓库当前版本可执行（不退化命令、不少写参数）

#### Scenario: 包含自检步骤
- **WHEN** 用户完成首跑
- **THEN** 章节给出至少 1 个「自检命令」验证后端可达（如 `curl http://localhost:8000/health`）+ 1 个验证前端可达（浏览器访问 URL）

### Requirement: README 必须覆盖 v1.0 已交付的全部能力

README 「功能特性」章节 MUST 列出 v1.0 已交付的所有业务能力，让用户在阅读 README 时即可了解系统能做什么，不必翻代码。

#### Scenario: 覆盖核心能力
- **WHEN** 用户阅读「功能特性」章节
- **THEN** MUST 涵盖以下 5 项：(1) 12-1 动量因子计算 (2) 参数化回测引擎（ETF 池 / 动量窗口 / 调仓频率 / top-N）(3) 6 个业绩指标（年化收益、最大回撤、夏普、Sortino、Calmar）(4) 实时 BUY/HOLD/WATCH 三态信号 (5) 4 个前端页面 + 18 个 REST 端点

#### Scenario: 业务能力清单与代码同步
- **WHEN** 章节列出能力清单
- **THEN** 每项 MUST 可在代码中找到对应实现（动量 → `app/factors/momentum.py`、回测 → `app/backtest/engine.py`、信号 → `app/signals/compute.py`、页面 → `frontend/src/pages/*.tsx`、API → `backend/app/api/v1/*.py`）

### Requirement: README 必须能解答「跑不起来怎么办」

README MUST 提供「常见问题」或「故障排查」章节，至少覆盖 3 类典型问题。

#### Scenario: 常见问题覆盖
- **WHEN** 用户遇到问题
- **THEN** MUST 在文档中找到对应章节：(1) 前端能开但 Dashboard 空（数据未同步） (2) 后端容器启动失败（端口占用 / 数据库权限） (3) akshare 同步失败（网络 / 限频）

### Requirement: backend/README 必须与现状一致

`backend/README.md` MUST 反映 v1.0 现状，不允许遗留 scaffold 阶段的内容。

#### Scenario: 测试数与现状一致
- **WHEN** 用户查阅测试覆盖说明
- **THEN** 测试数 MUST 与 `pytest --collect-only -q` 当前输出相符（允许标「约 N」但量级正确）

#### Scenario: 「后续计划」必须清空
- **WHEN** 用户阅读「后续计划」章节
- **THEN** MUST 不包含任何 v1.0 已交付的功能（无 Dashboard / Backtest UI / ETF 池管理 / 鉴权 / 任务调度 等 v1.0 已完成项）
- **AND** 可列出 v2.0 占位项（如多策略对比 / 美股扩展 / 实时告警），与 `spec/tasks.md` 对齐

### Requirement: frontend/README 必须列出全部页面与目录结构

`frontend/README.md` MUST 反映 v1.0 前端的完整结构，不允许遗漏已交付页面。

#### Scenario: 覆盖所有页面
- **WHEN** 用户阅读「目录结构」或「页面」章节
- **THEN** MUST 列出全部 4 个页面：HealthPage / DashboardPage / BacktestPage / PoolsPage
- **AND** MUST 提及 `Layout` 组件（导航 + Outlet）
- **AND** MUST 提及 Zustand store 列表

#### Scenario: 命令与 package.json 一致
- **WHEN** 章节给出 npm/pnpm 命令
- **THEN** 命令 MUST 来自 `frontend/package.json` 的 `scripts` 段（不允许发明脚本名）

### Requirement: 文档变更必须不破坏运行时

本次变更 MUST 是纯文档变更，不影响后端 / 前端 / Docker / 数据库 / 测试的任何行为。

#### Scenario: 无代码文件变更
- **WHEN** 用户执行 `git diff main -- '*.py' '*.tsx' '*.ts' '*.json' '*.toml' 'Dockerfile' 'docker-compose.yml' Makefile`
- **THEN** 输出 MUST 为空（仅有 `*.md` 文件的变更）

#### Scenario: 端到端仍可跑通
- **WHEN** 用户按更新后的 README 执行首跑
- **THEN** 系统行为与变更前一致（无功能回归）
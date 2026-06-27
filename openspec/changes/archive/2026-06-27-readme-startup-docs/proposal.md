## Why

v1.0 已完成（后端 + 前端 + REST API + 267 后端测试 + 190 前端测试），但 README 仍停留在脚手架阶段：

- 根 `README.md`（95 行）只写了 Docker Compose 启动，没提任何业务能力
- `backend/README.md` 末尾的「后续计划」把已交付的 Dashboard / Backtest UI / ETF 池管理列为 TODO；测试数（200）和实际（267）对不上
- `frontend/README.md` 只覆盖 HealthPage，没提 DashboardPage / BacktestPage / PoolsPage；目录结构列到 `pages/HealthPage.tsx` 为止

新用户 clone 下来跑 `make up` 后不知道下一步能做什么——不知道要跑 `alembic upgrade head`、不知道有 4 个前端页面、不知道 12 个 REST 端点的存在。这违背 v1.0「让个人投资者能跑起来看动量看板和调仓建议」的核心目标。

## What Changes

- **重写根 `README.md`**：覆盖 v1.0 完整能力（动量因子、回测、信号、4 个前端页面、12 个 API 端点）+ Docker 启动 + 本地开发 + 完整端到端首跑流程（up → migrate → sync → 打开浏览器）
- **更新 `backend/README.md`**：测试数 267、特性清单（含 sortino/calmar 持久化）、CLI 命令（`python -m app.data.sync` / `python -m app.data.signal`）、API 端点速查、目录结构补齐到 v1.0 状态
- **更新 `frontend/README.md`**：4 个页面说明、Layout 导航、Zustand store 列表、目录结构补齐
- **新增 `docs/QUICKSTART.md`**（或并入根 README「快速开始」章节）：5 分钟首次跑通流程（克隆 → `make up` → 迁移 → 同步 ETF 主数据 → 同步价格 → 打开 `localhost:5173/dashboard` → 跑首次回测）

不引入新代码、不改 API、不改测试。仅文档更新，对运行时零影响。

## Capabilities

### New Capabilities
- `user-onboarding`: 新用户首次跑通系统的完整流程（依赖 / 启动 / 初始化 / 同步 / 浏览）。覆盖 QUICKSTART 内容。
- `feature-inventory`: v1.0 已交付能力的清单（动量 / 回测 / 信号 / 前端页面 / API 端点 / CLI），作为 README 各章节的内容来源。

### Modified Capabilities
无（纯文档，无规格变更）

## Impact

- 文档：`README.md`（重写）、`backend/README.md`（更新）、`frontend/README.md`（更新）、新增 `docs/QUICKSTART.md`
- 无代码 / API / 依赖 / 数据库影响
- 无 breaking change
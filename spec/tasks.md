# 里程碑任务

## 总览

| 版本 | 主题 | 状态 |
|------|------|------|
| M0 | 项目初始化 | ✅ 进行中 |
| M1 | 后端骨架与配置 CRUD | 待启动 |
| M2 | 筛选核心迁移与单测 | 待启动 |
| M3 | 当日信号与持仓 API | 待启动 |
| M4 | 回测引擎 | 待启动 |
| M5 | 前端配置面板（池子/词典/参数） | 待启动 |
| M6 | 前端信号与持仓页 | 待启动 |
| M7 | 前端回测页 | 待启动 |
| M8 | 收盘数据同步 | 待启动 |

## 详细任务

### M0 项目初始化（当前）

- [x] 创建 `openspec/`、`spec/`、`backend/`、`frontend/`
- [x] 安装 `AGENTS.md`
- [x] 起草 `spec/requirements.md`、`design.md`、`tasks.md`、`structure.md`
- [ ] 初始化 Git 仓库
- [ ] 创建首个 `openspec/changes/` 变更（建议名 `bootstrap-fullstack`）

### M1 后端骨架与配置 CRUD

- FastAPI 项目结构
- SQLite + SQLModel
- `POST/GET/PUT/DELETE /api/configs/{pool|themes|strategy}`
- 单测：配置 CRUD

### M2 筛选核心迁移与单测（TDD 强制）

- 将 `main.py` 的 `filter_etfs()` 迁移到 `backend/app/services/screening.py`
- 去除 JoinQuant 全局函数依赖，改为显式参数
- 用 mock 数据源 + 真实 `numpy/pandas` 逻辑写单测

### M3 当日信号与持仓 API

- `GET /api/signals/today`（返回买卖建议）
- `GET /api/portfolio`（当前持仓）
- 单测覆盖

### M4 回测引擎

- `POST /api/backtest`
- 日级重放 + 净值序列 + 统计
- 单测覆盖

### M5 前端配置面板

- React 项目（Vite + Ant Design/shadcn）
- 池子、词典、参数三个配置页
- 调用 M1 API

### M6 前端信号与持仓页

- 当日买卖信号页（来自 M3）
- 持仓展示页（来自 M3）

### M7 前端回测页

- 时间区间选择 + 回测触发 + 净值曲线 + 统计展示
- 调用 M4 API

### M8 收盘数据同步

- 定时任务（cron / APScheduler）
- 调用 `MarketDataSource` 拉取数据入 DB

## 当前迭代

正在 M0，等待用户确认 `spec/requirements.md` 和 `design.md` 后进入首个 `openspec/changes/` 变更。
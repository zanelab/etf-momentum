# 里程碑任务

## 总览

| 版本 | 主题 | 状态 |
|------|------|------|
| M0 | 项目初始化 | ✅ 完成 |
| M1 | 后端骨架与配置 CRUD | ✅ 完成 |
| M2 | 筛选核心迁移与单测 | ✅ 完成 |
| M3 | 当日信号与持仓 API | ✅ 完成 |
| M4 | 回测引擎 | ✅ 完成 |
| M5 | 前端配置面板（池子/词典/参数） | ✅ 完成 |
| M6 | 前端信号与持仓页 | ✅ 完成 |
| M7 | 前端回测页 | ✅ 完成 |
| M8 | 收盘数据同步（mock） | ✅ 完成 |

## 详细任务

### M0 项目初始化

- [x] 创建 `openspec/`、`spec/`、`backend/`、`frontend/`
- [x] 安装 `AGENTS.md`
- [x] 起草 `spec/requirements.md`、`design.md`、`tasks.md`、`structure.md`
- [x] 初始化 Git 仓库
- [x] 创建首个 `openspec/changes/` 变更（`bootstrap-fullstack`，已归档）

### M1 后端骨架与配置 CRUD

- [x] FastAPI 项目结构
- [x] SQLite + SQLModel
- [x] `POST/GET/PUT/DELETE /api/configs/{pool|themes|strategy}`
- [x] 单测：配置 CRUD（`tests/test_configs.py`）

### M2 筛选核心迁移与单测（TDD 强制）

- [x] 将 `main.py` 的 `filter_etfs()` 迁移到 `backend/app/services/screening.py`
- [x] 去除 JoinQuant 全局函数依赖，改为显式参数
- [x] 用 mock 数据源 + 真实 `numpy/pandas` 逻辑写单测
- [x] JoinQuant shim 对照测试（`tests/test_screening_parity.py`，3 个用例）

### M3 当日信号与持仓 API

- [x] `GET /api/signals/today`（返回买卖建议）
- [x] `GET /api/portfolio`（当前持仓 + 市值 + 盈亏）
- [x] `GET /api/screening/today`（当日筛选目标）
- [x] 单测覆盖（`tests/test_signals.py` + `test_screening_api.py`）

### M4 回测引擎

- [x] `POST /api/backtest`（含 366 天窗口校验）
- [x] `GET /api/backtest/{task_id}`（BackgroundTask + JSON 文件持久化）
- [x] 日级重放 + 净值序列 + 统计（total_return / annualized_return / sharpe / max_drawdown / n_rebalances）
- [x] 单测覆盖（`tests/test_backtest.py`）

### M5 前端配置面板

- [x] React + Vite + TypeScript + Tailwind
- [x] 池子页（启用切换 / 删除 / 筛选）
- [x] 词典页（主题关键词分组编辑 + dirty/save）
- [x] 参数页（带类型校验的表单）
- [x] 调 M1 API

### M6 前端信号与持仓页

- [x] 信号页（卖出/买入卡片 + 原因/股数/盈亏）— 5s 轮询
- [x] 持仓页（市值/盈亏/总额）— 5s 轮询
- [x] 当日筛选目标页（chips）

### M7 前端回测页

- [x] 时间区间选择 + 回测触发（≤ 366 天）
- [x] recharts NAV 折线 + 4 项统计卡片
- [x] 任务状态轮询（2s，conditional）
- [x] 调 M4 API

### M8 收盘数据同步（mock）

- [x] `daily_sync.sync_today(target_date)` 读 fixture 末条写入 `backend/data/daily_sync/YYYY-MM-DD.json`
- [x] 当前以 fixture 末日作为 "today"（生产应替换为真实交易日历）

## 当前迭代

所有 M0–M8 里程碑已完成并归档（`openspec/changes/archive/bootstrap-fullstack-20260628/`）。下一迭代可在新变更中启动。
# 里程碑任务

## v1.0 — MVP（首个版本）

### 阶段 1：基础设施
- [x] 后端 FastAPI 脚手架 *(2026-06-26 完成，change: backend-fastapi-scaffold)*
- [x] 前端 Vite + React 脚手架 *(2026-06-26 完成，change: frontend-vite-react-scaffold)*
- [x] SQLite 数据模型（ETF, DailyPrice, BacktestRun, SignalSnapshot）*(2026-06-26 完成，change: sqlite-data-model)*
- [x] akshare 数据同步脚本 *(2026-06-26 完成，change: akshare-data-sync)*
- [x] Docker compose 本地启动 *(2026-06-26 完成，change: docker-compose)*

### 阶段 2：核心能力
- [x] 动量因子计算模块（12-1 动量）*(2026-06-26 完成，change: momentum-factor)*
- [x] 回测引擎（参数化：ETF 池、动量窗口、调仓频率）*(2026-06-26 完成，change: backtest-engine)*
- [x] 业绩指标计算（年化收益、最大回撤、夏普 + Sortino + Calmar）*(2026-06-26 完成，change: metrics-extraction)*
- [x] 实时信号计算与排名（BUY/HOLD/WATCH 三态 + CLI）*(2026-06-26 完成，change: realtime-signals)*

### 阶段 3：API + 前端
- [x] 后端 REST API（`/api/etfs`, `/api/signals`, `/api/backtest`）*(2026-06-26 完成，change: rest-api)*
- [x] 前端 Dashboard：动量排名 + 调仓建议 *(2026-06-26 完成，change: frontend-dashboard)*
- [x] 前端 Backtest UI：参数选择 + 业绩图表 *(2026-06-26 完成，change: frontend-backtest-ui)*
- [x] 前端 ETF 池管理 *(2026-06-27 完成，change: frontend-etf-pool-management)*

### 阶段 4：质量与交付
- [x] 后端单元测试（回测引擎、动量计算）*(2026-06-27 完成，change: backend-unit-tests-backtest-momentum；目标文件 78 → 130 测试)*
- [x] 前端组件测试*(2026-06-27 完成，change: frontend-component-tests；vitest 165 → 190 测试)*
- [x] README + 启动文档*(2026-06-27 完成，change: readme-startup-docs；3 个 README 重写 / 新增 5-min 首跑清单 / 18 端点速查表)*
- [x] v1.0 演示数据预置*(2026-06-27 完成，change: demo-data-v1；15 只 ETF × 1079 天 ≈ 16185 行 + signal + 宽基三杰 pool；后端测试 267 → 287)*

## v2.0 — 后续规划（占位）
- 多策略对比（双动量、相对动量）
- 美股 ETF 扩展
- 用户账户与策略持久化
- 实时告警（邮件 / 微信）

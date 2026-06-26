# 里程碑任务

## v1.0 — MVP（首个版本）

### 阶段 1：基础设施
- [ ] 后端 FastAPI 脚手架
- [ ] 前端 Vite + React 脚手架
- [ ] SQLite 数据模型（ETF, DailyPrice, BacktestRun, SignalSnapshot）
- [ ] akshare / baostock 数据同步脚本
- [ ] Docker compose 本地启动

### 阶段 2：核心能力
- [ ] 动量因子计算模块（12-1 动量）
- [ ] 回测引擎（参数化：ETF 池、动量窗口、调仓频率）
- [ ] 业绩指标计算（年化收益、最大回撤、夏普）
- [ ] 实时信号计算与排名

### 阶段 3：API + 前端
- [ ] 后端 REST API（`/api/etfs`, `/api/signals`, `/api/backtest`）
- [ ] 前端 Dashboard：动量排名 + 调仓建议
- [ ] 前端 Backtest UI：参数选择 + 业绩图表
- [ ] 前端 ETF 池管理

### 阶段 4：质量与交付
- [ ] 后端单元测试（回测引擎、动量计算）
- [ ] 前端组件测试
- [ ] README + 启动文档
- [ ] v1.0 演示数据预置

## v2.0 — 后续规划（占位）
- 多策略对比（双动量、相对动量）
- 美股 ETF 扩展
- 用户账户与策略持久化
- 实时告警（邮件 / 微信）

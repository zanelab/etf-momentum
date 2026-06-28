# Proposal: bootstrap-fullstack

## What

将原聚宽（JoinQuant）单文件 ETF 动量轮动策略 `main.py` 重构为前后端分离的全栈应用：

- **前端（React）**：提供配置 UI（静态核心池、主题分类词典、策略参数）、回测执行与展示、ETF 历史数据查询、当日买入/卖出信号、当前持仓展示。
- **后端（Python）**：提供 REST API；承载 ETF 筛选、回测、当日信号、持仓、收盘数据同步等业务逻辑；配置持久化；行情数据源抽象（默认 mock，可后续接入 akshare/tushare/聚宽）。

策略核心逻辑（双均线过滤、动量评分、行业分散、止损、防御 ETF）保持不变，只是从 JoinQuant 全局函数依赖迁移为显式参数注入的后端服务。

## Why

- 原 `main.py` 是聚宽平台单文件脚本，无法在本地开发/调试，配置全靠改源码。
- 配置（静态池、主题词典、策略参数）硬编码，无法在不修改代码的情况下调参或回测对比。
- 没有可视化界面，每日信号、持仓、回测结果都靠日志人工观察。
- 缺少单元测试框架，核心筛选逻辑难以保证正确性。
- 重构后可对接任意数据源，便于本地回测与未来实盘部署。

## Scope

- [x] backend
- [x] frontend

## Acceptance Criteria

### 后端

- [ ] `backend/` 提供 FastAPI 服务，`uvicorn backend.app.main:app` 可启动
- [ ] 配置持久化 API：`/api/configs/{pool|themes|strategy}` 支持 CRUD
- [ ] ETF 筛选 API：`/api/screening/today` 返回基于当前配置的目标 ETF 列表
- [ ] 当日信号 API：`/api/signals/today` 返回调仓建议（卖出列表 + 买入列表 + 数量）
- [ ] 持仓 API：`/api/portfolio` 返回当前持仓、成本价、市值、盈亏
- [ ] 回测 API：`/api/backtest` 支持时间区间 + 配置快照，回放筛选逻辑并返回净值序列与统计
- [ ] 历史数据 API：`/api/market/history` 返回 K 线/成交额
- [ ] 数据源抽象：`MarketDataSource` 接口 + mock 实现，可后续替换为真实数据源
- [ ] 核心筛选逻辑从 `main.py` 迁移至 `backend/app/services/screening.py`，去除 JoinQuant 全局函数依赖
- [ ] 筛选核心逻辑单测覆盖率 ≥ 80%（TDD 强制）
- [ ] SQLite 作为初始持久化存储

### 前端

- [ ] `frontend/` 提供 React 应用（Vite），`npm run dev` 可启动
- [ ] 静态核心池配置页：增删改查 ETF
- [ ] 主题分类词典配置页：增删改查主题关键词
- [ ] 策略参数配置页：可视化编辑动量周期、均线周期、止损比例等
- [ ] 当日信号页：展示买入/卖出建议
- [ ] 持仓展示页：展示持仓清单、成本、盈亏、止损线
- [ ] 回测页：时间区间选择 + 回测触发 + 净值曲线 + 统计展示
- [ ] ETF 历史数据查询页：单只 ETF K 线/成交额

### 工程

- [ ] 项目仍可通过 OpenSpec 工作流管理（state/gate/checkpoint/tdd 脚本）
- [ ] 原 `main.py` 保留作为参考（不删除，但文档说明已迁移）
- [ ] README 说明启动方式（后端 + 前端）
- [ ] `.env.example` 列出所需环境变量

## Out of Scope

- 实盘交易接入（仅回测与信号生成）
- 用户认证与多账户（单用户单账户）
- 行情数据源的选型与对接（保留 mock，由后续变更引入真实数据源）
- 移动端适配（仅桌面浏览器）

## Status

- [x] 提案已确认（2026-06-28）
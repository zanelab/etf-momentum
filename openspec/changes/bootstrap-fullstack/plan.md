# Implementation Plan: bootstrap-fullstack

> 任务按 M1–M8 里程碑组织。每项完成后立即跑 `./scripts/speccoding-tdd.sh verify <文件>` 验证（TDD 强制的实现文件）。
> 标记 `[TDD]` 的任务需要先写测试再写实现；标记 `[无测试]` 的任务主要是 UI/配置/脚本。
> 标记 `[后端]`/`[前端]`/`[共享]` 标识主要工作面。

## 1. 环境与依赖（Prerequisites）

- [x] 1.1 [后端] 创建 `backend/requirements.txt`（fastapi, uvicorn[standard], sqlmodel, pandas, numpy, pytest, httpx, pydantic, python-multipart）
- [x] 1.2 [后端] 创建 `backend/pyproject.toml` 或 `setup.cfg`，配置 ruff + pytest
- [x] 1.3 [后端] 创建 `backend/app/__init__.py` 与目录骨架
- [x] 1.4 [前端] 在 `frontend/` 初始化 Vite + React + TypeScript（手动创建配置文件）
- [x] 1.5 [前端] 安装基础依赖（react-router-dom, @tanstack/react-query, zustand, axios 或 fetch 封装）— `npm install` 完成（183 packages），`tsc --noEmit` 通过
- [x] 1.6 [前端] 初始化 shadcn/ui（components.json + tailwind + lib/utils 已就位；具体组件按页面需要时 `npx shadcn add`）
- [x] 1.7 [共享] README 列出启动命令（后端 venv + 前端 npm run dev）

## 2. 后端骨架（M1）

- [x] 2.1 [后端][TDD] 创建 `backend/app/main.py`：FastAPI 实例 + CORS + `/api/health`
- [x] 2.2 [后端][TDD] 创建 SQLModel 模型：`StaticPool`、`ThemeKeyword`、`StrategyParam`（`backend/app/models/`）
- [x] 2.3 [后端] 创建 `backend/app/db.py`：engine + session + 初始化逻辑
- [x] 2.4 [后端] 创建 `backend/app/seed.py`：首次启动时种入默认数据（静态池 ~145 只、主题词典 17 类、策略参数）
- [x] 2.5 [后端][TDD] 实现 `GET/POST/PUT/DELETE /api/configs/pool`（`backend/app/api/configs.py`）
- [x] 2.6 [后端][TDD] 实现 `GET/PUT /api/configs/themes`
- [x] 2.7 [后端][TDD] 实现 `GET/PUT /api/configs/strategy`
- [x] 2.8 [后端][TDD] 配置 API 单测：`backend/tests/test_configs.py`

## 3. 数据源 + fixture（M2 准备）

- [x] 3.1 [后端] 定义 `MarketDataSource` Protocol（`backend/app/data_sources/base.py`）
- [x] 3.2 [后端][TDD] 实现 `FixtureCSVSource`（`backend/app/data_sources/fixture.py`）
- [x] 3.3 [后端] fixture 生成脚本 `backend/scripts/generate_fixtures.py`：为 10 只代表性 ETF 生成 2 年日级 CSV（GBM 模拟 + 真实 ETF 量级噪声）
- [x] 3.4 [后端] 生成 fixture 文件，写入 `backend/data/fixtures/`，提交到 git
- [x] 3.5 [后端][TDD] 数据源单测：`backend/tests/test_fixture_source.py`

## 4. 筛选核心迁移（M2，TDD 强制）

- [x] 4.1 [后端][TDD] 定义 `StrategyParams`、`ScreeningContext` Pydantic 模型（`backend/app/services/types.py`）
- [x] 4.2 [后端][TDD] 迁移 `filter_etfs()` 签名：`filter_etfs(as_of, static_pool, dynamic_pool, themes, params, market) -> list[str]`
- [x] 4.3 [后端][TDD] 迁移双均线过滤逻辑（`backend/app/services/screening.py`）
- [x] 4.4 [后端][TDD] 迁移动量评分逻辑（加权对数回归 + R²）
- [x] 4.5 [后端][TDD] 迁移行业分散选取逻辑（含兜底补齐）
- [x] 4.6 [后端][TDD] 单测覆盖：无目标、行业分散、动量异常值、成交量过滤、防御 ETF 排除
- [x] 4.7 [后端] 对照测试：3 组 fixture 输入，原 `main.py`（带 shim 适配）vs 新实现，结果一致

## 5. 当日信号与持仓 API（M3）

- [x] 5.1 [后端][TDD] 实现 `GET /api/screening/today`
- [x] 5.2 [后端] mock 持仓数据：`backend/app/services/portfolio_mock.py`（3 只 ETF，含成本价）
- [x] 5.3 [后端][TDD] 实现 `GET /api/portfolio`（市值、P&L 计算）
- [x] 5.4 [后端][TDD] 实现 `GET /api/signals/today`：基于筛选 + 持仓生成调仓建议（卖出/买入/数量）
- [x] 5.5 [后端][TDD] 信号单测：`backend/tests/test_signals.py`

## 6. 回测引擎（M4）

- [x] 6.1 [后端][TDD] 实现 `run_backtest()` 服务（`backend/app/services/backtest.py`）：日级重放 + 净值计算 + 统计
- [x] 6.2 [后端] 任务状态文件持久化：`backend/data/backtest_tasks/{task_id}.json`
- [x] 6.3 [后端][TDD] 实现 `POST /api/backtest`：创建任务 + BackgroundTask 启动
- [x] 6.4 [后端][TDD] 实现 `GET /api/backtest/{task_id}`：查询状态/结果
- [x] 6.5 [后端][TDD] 回测单测：`backend/tests/test_backtest.py`（小区间，固定结果断言）
- [x] 6.6 [后端] 区间超过 1 年返回 400

## 7. 历史数据 API

- [x] 7.1 [后端][TDD] 实现 `GET /api/market/history`
- [x] 7.2 [后端][TDD] 实现 `GET /api/market/list`
- [x] 7.3 [后端][TDD] 市场 API 单测

## 8. 前端项目骨架（M5 准备）

- [ ] 8.1 [前端] 配置 vite.config.ts 代理 `/api` 到 `http://localhost:8000`
- [ ] 8.2 [前端] 创建 `src/api/client.ts`：fetch 封装 + 错误处理
- [ ] 8.3 [前端] 创建 `src/api/hooks.ts`：TanStack Query hooks（usePool, useThemes, useStrategy, useSignals, usePortfolio, useBacktest, useMarket）
- [ ] 8.4 [前端] 创建路由结构（react-router-dom）：/pool, /themes, /strategy, /signals, /portfolio, /backtest, /history
- [ ] 8.5 [前端] 创建 AppShell：导航 + 主题（shadcn）

## 9. 前端配置面板（M5）

- [ ] 9.1 [前端] PoolConfig.tsx — Table + 新增对话框 + 启用/禁用 toggle + 删除
- [ ] 9.2 [前端] ThemeConfig.tsx — 主题分组编辑（accordion 或 tabs）
- [ ] 9.3 [前端] StrategyConfig.tsx — Form（数值输入 + 开关 + select）
- [ ] 9.4 [前端] 三个页面调用对应 API hook，错误用 toast 提示

## 10. 前端信号与持仓（M6）

- [ ] 10.1 [前端] Signals.tsx — 卖/买卡片（reason 标签、目标数量）+ 轮询 5s
- [ ] 10.2 [前端] Portfolio.tsx — Table + Statistic（总市值、总盈亏）+ 轮询 5s

## 11. 前端回测（M7）

- [ ] 11.1 [前端] 安装图表库（recharts 或 lightweight-charts）
- [ ] 11.2 [前端] Backtest.tsx — DatePicker + 提交按钮 + 进度轮询 2s
- [ ] 11.3 [前端] 净值曲线组件（双曲线：本策略 vs 基准）
- [ ] 11.4 [前端] 统计指标卡片（total_return, sharpe, max_drawdown）

## 12. 前端历史数据

- [ ] 12.1 [前端] History.tsx — 单只 ETF K 线图 + 成交额
- [ ] 12.2 [前端] 输入框选择 ETF code

## 13. 收盘同步（mock 实现）

- [ ] 13.1 [后端] 实现 `daily_sync.py`：写入 fake 收盘价（mock）
- [ ] 13.2 [后端] 在 startup 事件中调用一次
- [ ] 13.3 [后端][TDD] 单测

## 14. 集成验证

- [ ] 14.1 [共享] 后端启动测试：`uvicorn backend.app.main:app`，健康检查返回 200
- [ ] 14.2 [共享] 前端启动测试：`npm run dev`，所有页面路由可达
- [ ] 14.3 [共享] 端到端：浏览器打开前端，能配置池子、触发回测、看到结果
- [ ] 14.4 [共享] 完善 README：启动步骤 + 端口 + 已知限制（mock 数据）
- [ ] 14.5 [共享] 完善 `.env.example`：列出 `FIXTURES_DIR`、`BACKTEST_TASK_DIR` 等
- [ ] 14.6 [共享] 验证 `main.py` 头部包含迁移提示注释

## 15. CI / 提交前检查

- [ ] 15.1 [后端] `pytest backend/tests/` 通过
- [ ] 15.2 [后端] `ruff check backend/` 通过
- [ ] 15.3 [前端] `tsc --noEmit` 通过
- [ ] 15.4 [前端] `npm run build` 通过
- [ ] 15.5 [共享] `./scripts/speccoding-tdd.sh check-commit` 通过

## 总任务数

共 ~50 个 checkbox，分布：
- 后端实现（TDD 强制）：~25 项
- 后端配置/脚本：[无测试]：~8 项
- 前端实现：[无测试]：~12 项
- 集成验证：~5 项
# Checkpoint

**写入时间**: 2026-06-28T09:26:04Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: bootstrap-fullstack
**分支**: feature/bootstrap-fullstack
**父分支**: main
**Plan 进度**: 15/72

## 未完成的 Plan 项

```
30:- [ ] 3.1 [后端] 定义 `MarketDataSource` Protocol（`backend/app/data_sources/base.py`）
31:- [ ] 3.2 [后端][TDD] 实现 `FixtureCSVSource`（`backend/app/data_sources/fixture.py`）
32:- [ ] 3.3 [后端] fixture 生成脚本 `backend/scripts/generate_fixtures.py`：为 10 只代表性 ETF 生成 2 年日级 CSV（GBM 模拟 + 真实 ETF 量级噪声）
33:- [ ] 3.4 [后端] 生成 fixture 文件，写入 `backend/data/fixtures/`，提交到 git
34:- [ ] 3.5 [后端][TDD] 数据源单测：`backend/tests/test_fixture_source.py`
38:- [ ] 4.1 [后端][TDD] 定义 `StrategyParams`、`ScreeningContext` Pydantic 模型（`backend/app/services/types.py`）
39:- [ ] 4.2 [后端][TDD] 迁移 `filter_etfs()` 签名：`filter_etfs(as_of, static_pool, dynamic_pool, themes, params, market) -> list[str]`
40:- [ ] 4.3 [后端][TDD] 迁移双均线过滤逻辑（`backend/app/services/screening.py`）
41:- [ ] 4.4 [后端][TDD] 迁移动量评分逻辑（加权对数回归 + R²）
42:- [ ] 4.5 [后端][TDD] 迁移行业分散选取逻辑（含兜底补齐）
43:- [ ] 4.6 [后端][TDD] 单测覆盖：无目标、行业分散、动量异常值、成交量过滤、防御 ETF 排除
44:- [ ] 4.7 [后端] 对照测试：3 组 fixture 输入，原 `main.py`（带 shim 适配）vs 新实现，结果一致
48:- [ ] 5.1 [后端][TDD] 实现 `GET /api/screening/today`
49:- [ ] 5.2 [后端] mock 持仓数据：`backend/app/services/portfolio_mock.py`（3 只 ETF，含成本价）
50:- [ ] 5.3 [后端][TDD] 实现 `GET /api/portfolio`（市值、P&L 计算）
51:- [ ] 5.4 [后端][TDD] 实现 `GET /api/signals/today`：基于筛选 + 持仓生成调仓建议（卖出/买入/数量）
52:- [ ] 5.5 [后端][TDD] 信号单测：`backend/tests/test_signals.py`
56:- [ ] 6.1 [后端][TDD] 实现 `run_backtest()` 服务（`backend/app/services/backtest.py`）：日级重放 + 净值计算 + 统计
57:- [ ] 6.2 [后端] 任务状态文件持久化：`backend/data/backtest_tasks/{task_id}.json`
58:- [ ] 6.3 [后端][TDD] 实现 `POST /api/backtest`：创建任务 + BackgroundTask 启动
```

## 最近修改的文件

```
6a4ee98 feat: bootstrap-fullstack section 1 — environment & dependencies
8a5648d chore: start bootstrap-fullstack change
7529e74 chore: bootstrap SpecCoding workflow and fullstack architecture
```

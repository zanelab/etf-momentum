# Implementation Plan: 回测引擎

## Prerequisites
- [x] 切换到 feature/backtest-engine 分支
- [x] 确认 backend 目录存在，动量因子 + 数据层就位
- [x] 确认 Python 3.11+ 与 uv 可用

## Dependencies
- [x] 无新增运行时依赖（仅用 stdlib `decimal.Decimal`、`enum.Enum`、`dataclasses`）
- [x] 复用 `app.factors.momentum.compute_momentum_scores` + `rank_scores`
- [x] 确认 `backend/pyproject.toml` 无需更新

## Module Structure
- [x] `app/backtest/__init__.py` 创建空包文件
- [x] `app/backtest/__init__.py` 从 `app.backtest.engine` re-export BacktestParams / RebalanceFrequency / RebalanceEvent / BacktestResult / run_backtest
- [x] `app/backtest/__init__.py` 从 `app.backtest.persistence` re-export save_backtest_run

## Engine Implementation
- [x] `app/backtest/engine.py` 定义 `RebalanceFrequency(Enum)`，含 MONTHLY / QUARTERLY
- [x] `app/backtest/engine.py` 定义 `BacktestParams(frozen=True)`：etf_pool / start / end / initial_cash / lookback=252 / skip=21 / top_n=5 / rebalance_freq=MONTHLY
- [x] `app/backtest/engine.py` 定义 `RebalanceEvent(frozen=True)`：date / scores / selected / weights
- [x] `app/backtest/engine.py` 定义 `BacktestResult`：nav_series / rebalance_log / metrics
- [x] `app/backtest/engine.py` 实现 `_validate_params(params, price_history)`
- [x] `app/backtest/engine.py` 实现 `_build_calendar(price_history, start, end)`：union of dates 排序去重
- [x] `app/backtest/engine.py` 实现 `_find_rebalance_dates(calendar, freq)`：按月/季分组取最后交易日
- [x] `app/backtest/engine.py` 实现 `_close_at(price_history, date)`：返回 code→close 映射
- [x] `app/backtest/engine.py` 实现 `_compute_scores(price_history, params, rebalance_date)`：对每只 ETF 切片 closes → compute_momentum_scores
- [x] `app/backtest/engine.py` 实现 `_compute_metrics(nav_series, initial_cash)`：total_return / annualized_return / max_drawdown / sharpe_ratio
- [x] `app/backtest/engine.py` 实现 `run_backtest(params, price_history)`：主循环 mark-to-market + rebalance

## Persistence Implementation
- [x] `app/backtest/persistence.py` 实现 `save_backtest_run(session, params, result)`
  - [x] 构造 BacktestRun：name=None / etf_pool=list / momentum_window=lookback / rebalance_freq=value / start_date / end_date / metrics=dict
  - [x] metrics 含 params 子字典（lookback/skip/top_n/initial_cash/final_nav 字符串化）
  - [x] session.add + commit + refresh；失败抛异常不静默

## Testing
- [x] `tests/test_backtest_engine.py` 创建
- [x] `test_backtest_params_defaults`：构造 BacktestParams，验证默认值
- [x] `test_backtest_params_frozen`：尝试修改 → FrozenInstanceError
- [x] `test_rebalance_frequency_values`：MONTHLY / QUARTERLY .value
- [x] `test_rebalance_event_construction`：RebalanceEvent 字段类型
- [x] `test_backtest_result_construction`：BacktestResult 字段类型
- [x] `test_run_backtest_three_etfs_monthly`：3 只 ETF 月末调仓，验证 selected 长度 2 / weights 之和 = 1 / rebalance_log 3 条
- [x] `test_run_backtest_single_etf`：单只 ETF → 全部资金进一只
- [x] `test_run_backtest_no_rebalance_all_insufficient`：所有 ETF 数据不足 → rebalance_log 空 / NAV 平直 / total_return=0
- [x] `test_run_backtest_short_window`：日期范围太短 → 同上
- [x] `test_run_backtest_monthly_vs_quarterly`：同区间 MONTHLY 12 次 vs QUARTERLY 4 次
- [x] `test_run_backtest_rebalance_day_no_close`：调仓日某 ETF 无数据 → 跳过买入
- [x] `test_run_backtest_delisted_etf_sold_to_cash`：中途 ETF 数据终止 → 卖出转现金
- [x] `test_run_backtest_top_n_exceeds_available`：top_n=5 但只有 3 只可用 → 全部入选 / 等分
- [x] `test_run_backtest_weights_sum_to_one`：任意调仓事件 weights 之和 == 1
- [x] `test_metrics_total_return_known`：final=120000 / initial=100000 → 0.2
- [x] `test_metrics_annualized_one_year`：365 天 +20% → annualized ≈ 0.2
- [x] `test_metrics_max_drawdown_known`：NAV [100,120,60,80] → max_dd = 0.5
- [x] `test_metrics_sharpe_known`：已知日收益 → 手算
- [x] `test_metrics_sharpe_zero_std`：NAV 平直 → sharpe = None
- [x] `tests/test_backtest_persistence.py` 创建
- [x] `test_save_backtest_run_writes_orm`：mock session 验证 add/commit/refresh 调用
- [x] `test_save_backtest_run_metrics_serialized`：metrics 是 JSON dict 含全部指标 + params 子字典
- [x] `test_save_backtest_run_propagates_exception`：commit 抛 IntegrityError → 向上传播

## TDD Verification
- [x] 写完 22+ 个测试后运行 pytest 全部通过

## Build & Runtime Verification
- [x] `cd backend && uv run pytest` → 全部通过（90+：68 原有 + 22+ 新增）
- [x] `cd backend && uv run python -c "from app.backtest import BacktestParams, run_backtest; print(BacktestParams.__doc__)"` → 正常

## Documentation
- [x] `backend/README.md` 增补「回测引擎」章节：
  - BacktestParams 字段说明
  - run_backtest 调用示例（含最小价格历史 fixture）
  - save_backtest_run 示例
  - 业绩指标公式
  - 设计决策表（同 proposal）

## Acceptance Check
- [x] 逐条对照 proposal.md 的 13 项 Acceptance Criteria，全部满足
- [x] 逐条对照 spec.md 的 8 个 Requirement 至少一个 Scenario 通过
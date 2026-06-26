# Checkpoint

**写入时间**: 2026-06-26T08:15:48Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: backtest-engine
**分支**: feature/backtest-engine
**父分支**: main
**Plan 进度**: 0/54

## 未完成的 Plan 项

```
4:- [ ] 切换到 feature/backtest-engine 分支
5:- [ ] 确认 backend 目录存在，动量因子 + 数据层就位
6:- [ ] 确认 Python 3.11+ 与 uv 可用
9:- [ ] 无新增运行时依赖（仅用 stdlib `decimal.Decimal`、`enum.Enum`、`dataclasses`）
10:- [ ] 复用 `app.factors.momentum.compute_momentum_scores` + `rank_scores`
11:- [ ] 确认 `backend/pyproject.toml` 无需更新
14:- [ ] `app/backtest/__init__.py` 创建空包文件
15:- [ ] `app/backtest/__init__.py` 从 `app.backtest.engine` re-export BacktestParams / RebalanceFrequency / RebalanceEvent / BacktestResult / run_backtest
16:- [ ] `app/backtest/__init__.py` 从 `app.backtest.persistence` re-export save_backtest_run
19:- [ ] `app/backtest/engine.py` 定义 `RebalanceFrequency(Enum)`，含 MONTHLY / QUARTERLY
20:- [ ] `app/backtest/engine.py` 定义 `BacktestParams(frozen=True)`：etf_pool / start / end / initial_cash / lookback=252 / skip=21 / top_n=5 / rebalance_freq=MONTHLY
21:- [ ] `app/backtest/engine.py` 定义 `RebalanceEvent(frozen=True)`：date / scores / selected / weights
22:- [ ] `app/backtest/engine.py` 定义 `BacktestResult`：nav_series / rebalance_log / metrics
23:- [ ] `app/backtest/engine.py` 实现 `_validate_params(params, price_history)`
24:- [ ] `app/backtest/engine.py` 实现 `_build_calendar(price_history, start, end)`：union of dates 排序去重
25:- [ ] `app/backtest/engine.py` 实现 `_find_rebalance_dates(calendar, freq)`：按月/季分组取最后交易日
26:- [ ] `app/backtest/engine.py` 实现 `_close_at(price_history, date)`：返回 code→close 映射
27:- [ ] `app/backtest/engine.py` 实现 `_compute_scores(price_history, params, rebalance_date)`：对每只 ETF 切片 closes → compute_momentum_scores
28:- [ ] `app/backtest/engine.py` 实现 `_compute_metrics(nav_series, initial_cash)`：total_return / annualized_return / max_drawdown / sharpe_ratio
29:- [ ] `app/backtest/engine.py` 实现 `run_backtest(params, price_history)`：主循环 mark-to-market + rebalance
```

## 最近修改的文件

```
7832e3b chore(state): record momentum-factor merge progress
c779d0d Merge feature/momentum-factor: 12-1 momentum pure-function module
7e8b695 chore(archive): complete momentum-factor change
8534fe8 feat(factors): 12-1 momentum pure-function module
10d84cd chore(state): mark code_pushed=true
```

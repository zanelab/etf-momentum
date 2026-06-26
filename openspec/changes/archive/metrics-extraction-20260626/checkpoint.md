# Checkpoint

**写入时间**: 2026-06-26T08:45:59Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: metrics-extraction
**分支**: feature/metrics-extraction
**父分支**: main
**Plan 进度**: 0/43

## 未完成的 Plan 项

```
4:- [ ] 切换到 feature/metrics-extraction 分支
5:- [ ] 确认 backend 目录存在，回测引擎就位
6:- [ ] 确认 Python 3.11+ 与 uv 可用
9:- [ ] 无新增运行时依赖
10:- [ ] 确认 `backend/pyproject.toml` 无需更新
13:- [ ] `app/backtest/metrics.py` 创建
14:- [ ] `app/backtest/__init__.py` re-export `compute_metrics`
17:- [ ] `app/backtest/metrics.py` 实现 `compute_metrics(nav_series, initial_cash, *, risk_free_rate=Decimal("0")) -> dict[str, Decimal | None]`
18:- [ ] `app/backtest/metrics.py` 实现 `_annualized_ratio(excess_returns, raw_returns_for_std)` 内部辅助
19:- [ ] `app/backtest/metrics.py` 实现 `_decimal_pow(base, exponent)`（从 engine 迁移）
20:- [ ] `app/backtest/metrics.py` 实现 `_zero_metrics()` 返回空序列默认 dict
23:- [ ] `app/backtest/engine.py` 删除 `_compute_metrics` 函数体
24:- [ ] `app/backtest/engine.py` 删除 `_decimal_pow` 函数体
25:- [ ] `app/backtest/engine.py` 增加 `from app.backtest.metrics import compute_metrics`
26:- [ ] `app/backtest/engine.py` `run_backtest` 内 `_compute_metrics(nav_series, params.initial_cash)` → `compute_metrics(nav_series, params.initial_cash)`
29:- [ ] `tests/test_backtest_metrics.py` 创建
30:- [ ] `test_total_return_known`：100 → 120 = 0.2
31:- [ ] `test_total_return_negative`：100 → 80 = -0.2
32:- [ ] `test_annualized_return_one_year`：365 天 +20% → ~0.2
33:- [ ] `test_annualized_short_window`：7 天 +1% → 大幅年化
```

## 最近修改的文件

```
dda2b01 chore(state): record backtest-engine merge progress
dd17900 Merge feature/backtest-engine: momentum backtest engine + ORM persistence
59c8519 chore(archive): complete backtest-engine change
30ff23a feat(backtest): momentum backtest engine + ORM persistence
7832e3b chore(state): record momentum-factor merge progress
```

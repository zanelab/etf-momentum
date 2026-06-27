# Tasks — Backend Unit Tests (Backtest Engine + Momentum)

## 1. Validation tests (new file)

- [x] 1.1 Create `backend/tests/test_engine_validation.py` with `TestValidateParams` class
- [x] 1.2 Test `end < start` raises `ValueError` containing "end"
- [x] 1.3 Test `initial_cash <= 0` (zero + negative) raises `ValueError` containing "initial_cash"
- [x] 1.4 Test `top_n < 1` (zero + negative) raises `ValueError` containing "top_n"
- [x] 1.5 Test `lookback < 1` raises `ValueError` containing "lookback"
- [x] 1.6 Test `skip < 0` raises `ValueError` containing "skip"
- [x] 1.7 Test empty `etf_pool` raises `ValueError` containing "empty"
- [x] 1.8 Test missing pool codes raises `ValueError` containing "missing"

## 2. Engine edge-case tests (extend `test_backtest_engine.py`)

- [x] 2.1 Add `TestEngineEdgeCases` class to `test_backtest_engine.py`
- [x] 2.2 Test empty calendar (no price data in `[start, end]`) → 0 rebalances, NAV constant
- [x] 2.3 Test all selected top-N have non-positive close on rebalance day → no buy, no event
- [x] 2.4 Test all ETF scores `None` on rebalance day → rebalance skipped (no event)
- [x] 2.5 Test cross-year monthly rebalance: last event's `date.month == 12`
- [x] 2.6 Test single-day calendar (1 trading day in window) → at most 1 rebalance if month/quarter-end
- [x] 2.7 Test `sum(weights) == Decimal("1")` for 1, 2, 3, 5 buy codes
- [x] 2.8 Test single-ETF rebalance → that ETF's weight is `Decimal("1")` exactly
- [x] 2.9 Test delisted on first day of window → NAV = initial_cash (all cash)
- [x] 2.10 Test sell-then-rebuy on rebalance day → NAV unchanged across the rebalance
- [x] 2.11 Test weight quantization: last code carries residual (verifies `_quantize` logic)
- [x] 2.12 Test `_build_calendar` filters dates outside `[start, end]` (helper-direct unit test)

## 3. Metrics + persistence tests (extend `test_backtest_metrics.py` / `test_backtest_persistence.py`)

- [x] 3.1 Add `test_sortino_with_risk_free_rate` — sortino at rf=0.02 < sortino at rf=0
- [x] 3.2 Add `test_sharpe_all_excess_negative` — series with all negative excess returns → ratio still computable (not None)
- [x] 3.3 Add `test_sharpe_insufficient_excess_returns` — 1 daily return → sharpe None
- [x] 3.4 Add `test_annualized_days_one` — two dates 1 day apart → annualized ≈ 0
- [x] 3.5 Add `test_decimal_pow_negative_base` — `_decimal_pow(Decimal("-2"), Decimal("0.5"))` returns 0
- [x] 3.6 Add `test_annualized_ratio_single_element` — list of 1 → returns None
- [x] 3.7 Add `test_metrics_contains_sortino_calmar` to `test_backtest_persistence.py`
- [x] 3.8 Add `test_metrics_sortino_calmar_none` — None values serialize as null
- [x] 3.9 Add `test_save_with_name` — `name` field set in row
- [x] 3.10 Add `test_save_single_point_nav` — single `(date, nav)` → `final_nav` populated

## 4. Momentum edge cases (extend `test_momentum.py`)

- [x] 4.1 Add `test_lookback_zero_returns_zero` — `lookback=0, skip=0` → result 0
- [x] 4.2 Add `test_skip_zero_uses_last_close` — `skip=0` with valid history → result computable
- [x] 4.3 Add `test_scores_with_override_params` — `compute_momentum_scores(history, lookback=60, skip=5)` propagates
- [x] 4.4 Add `test_very_large_prices` — prices 1e6+ don't lose precision
- [x] 4.5 Add `test_mixed_types_in_closes` — `[Decimal, float, Decimal]` → None (no silent cast)

## 5. Verification

- [x] 5.1 Run `pytest backend/tests -v` and confirm 0 failures (267 passed)
- [x] 5.2 Run target files and confirm new tests are picked up (130 passed in 5 target files, was 78)
- [x] 5.3 Run `git diff --stat` and confirm only test files changed (no `app/` modifications) — `persistence.py` has +2 lines documented in design.md
- [x] 5.4 Total test count grows from 78 → 130 in target files (+52 new tests)

# Test Coverage — Backtest Engine + Momentum

> 本次变更的产品行为不变，仅在后端测试套件中显式锁定以下契约。这些 Requirement 定义了「在合并前必须通过的测试」。

## ADDED Requirements

### Requirement: _validate_params raises ValueError for invalid inputs

The `app.backtest.engine._validate_params` function MUST raise `ValueError` with a descriptive message when any of the following conditions hold:
- `params.end < params.start`
- `params.initial_cash <= 0`
- `params.top_n < 1`
- `params.lookback < 1`
- `params.skip < 0`
- `params.etf_pool` is empty
- any code in `params.etf_pool` is missing from `price_history`

#### Scenario: end before start
- **WHEN** `BacktestParams(end=date(2024, 1, 1), start=date(2024, 12, 31), ...)` is constructed and `run_backtest` is called
- **THEN** `ValueError` is raised whose message contains "end"

#### Scenario: missing pool codes
- **WHEN** `BacktestParams(etf_pool=["a", "b"], ...)` is passed with `price_history={"a": [...]}` (no "b")
- **THEN** `ValueError` is raised whose message contains "missing"

### Requirement: run_backtest rebalance edges are deterministic

The `run_backtest` function MUST produce stable results for these edge cases:
- Empty calendar (no price data in `[start, end]`) → zero rebalance events, total_return = 0, NAV constant.
- All selected top-N have non-positive close on a rebalance day → no buy for that rebalance, no `RebalanceEvent` appended for it.
- All ETF scores are `None` on a rebalance day → rebalance skipped (no event).
- Cross-year rebalance: Dec 31 of year N is a valid monthly rebalance; Jan 1 of year N+1 is not.

#### Scenario: empty calendar
- **WHEN** `price_history` contains no dates within `[start, end]`
- **THEN** `result.rebalance_log == []` and `result.metrics["total_return"] == Decimal("0")`

#### Scenario: cross-year monthly rebalance
- **WHEN** the calendar includes Dec 31 of year N and the engine runs with MONTHLY frequency
- **THEN** the last `rebalance_log` entry's `date` is Dec 31 of year N

### Requirement: Rebalance weights sum to exactly Decimal("1")

After every `RebalanceEvent`, `sum(event.weights.values())` MUST equal `Decimal("1")` exactly (no rounding error), regardless of how many `buy_codes` were selected (1, 2, 3, ...).

#### Scenario: 3 buy codes
- **WHEN** a rebalance selects 3 codes
- **THEN** `sum(event.weights.values()) == Decimal("1")` and the last code carries the residual

#### Scenario: 1 buy code
- **WHEN** a rebalance selects exactly 1 code
- **THEN** that code's weight is `Decimal("1")`

### Requirement: sortino_ratio and calmar_ratio are persisted to metrics JSON

`save_backtest_run` MUST include `sortino_ratio` and `calmar_ratio` (in addition to the existing 4 keys) in the serialized `BacktestRun.metrics` JSON, and MUST round-trip Decimal values as strings and `None` as `null`.

#### Scenario: round-trip Decimal
- **WHEN** `BacktestResult.metrics` contains `sortino_ratio=Decimal("1.5")` and `calmar_ratio=Decimal("2.0")`
- **THEN** the persisted JSON has `"sortino_ratio": "1.5"` and `"calmar_ratio": "2.0"`

#### Scenario: round-trip None
- **WHEN** `BacktestResult.metrics` contains `sortino_ratio=None` and `calmar_ratio=None`
- **THEN** the persisted JSON has `null` for both keys

### Requirement: compute_metrics honors risk_free_rate for sortino

`compute_metrics` MUST apply the `risk_free_rate` parameter to the `sortino_ratio` calculation (subtracting the per-day risk-free rate from the negative-return population), the same way it does for `sharpe_ratio`.

#### Scenario: non-zero risk_free_rate lowers sortino
- **WHEN** a NAV series produces a negative sortino at `risk_free_rate=0`
- **THEN** the sortino at `risk_free_rate=Decimal("0.02")` is strictly smaller (more negative)

### Requirement: compute_momentum_score handles lookback=0 and skip=0

`compute_momentum_score` MUST return a finite Decimal (or `None` for insufficient data) for the boundary cases `lookback=0` and `skip=0`, and MUST propagate the custom `lookback` / `skip` parameters when called via `compute_momentum_scores`.

#### Scenario: lookback=0 with sufficient data
- **WHEN** `compute_momentum_score(closes, lookback=0, skip=0)` is called with at least 1 valid close
- **THEN** the result is `Decimal("0")` (close / close - 1)

#### Scenario: compute_momentum_scores uses override
- **WHEN** `compute_momentum_scores(history, lookback=60, skip=5)` is called with histories shorter than 273 days but ≥ 66 days
- **THEN** scores are computed using the 60/5 window

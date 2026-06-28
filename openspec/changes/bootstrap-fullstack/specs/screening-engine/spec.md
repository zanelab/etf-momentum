## ADDED Requirements

### Requirement: ETF screening engine
The system SHALL provide a pure-function screening service `filter_etfs(as_of, static_pool, dynamic_pool, themes, params, market)` that returns the day's target ETF list based on dual-MA filter, momentum scoring, and industry diversification logic migrated from the original `main.py`.

#### Scenario: All candidates filtered by dual MA
- **WHEN** `enable_ma_filter` is true and no ETF in the combined pool has `close > MA_short and MA_short > MA_long`
- **THEN** screening returns an empty list and logs "no candidate passed MA filter"

#### Scenario: Momentum scoring with weighted linear regression
- **WHEN** at least one ETF passes the MA filter
- **THEN** for each candidate the system MUST compute `score = annual_return × R²` using weighted log-linear regression with `weights = linspace(1, 2, n)` and filter `0 < score < 5`

#### Scenario: Industry diversification picks one per theme
- **WHEN** `enable_industry_diverse` is true and `stock_sum` = 1
- **THEN** system MUST select the highest-scoring ETF from each theme in order until `stock_sum` is reached, and SHALL fall back to non-diversified selection if insufficient themes exist

#### Scenario: Volume spike filter
- **WHEN** an ETF's projected today volume > `volume_threshold × avg_volume_lookback`
- **THEN** system MUST exclude it from scoring

#### Scenario: Defensive ETF exclusion
- **WHEN** `defensive_etf` is in any pool
- **THEN** system MUST exclude it from scoring (it's a fallback target, not a candidate)
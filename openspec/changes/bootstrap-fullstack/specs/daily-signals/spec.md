## ADDED Requirements

### Requirement: Daily trading signals
The system SHALL expose `GET /api/signals/today` returning today's rebalance suggestions (sells and buys) by combining screening output with current portfolio state.

#### Scenario: Targets absent — switch to defensive
- **WHEN** screening returns an empty list
- **THEN** system returns `{ "to_sell": [...non-defensive-holdings], "to_buy": [{ "code": "<defensive_etf>", ... }] }` if `defensive_etf` is tradable

#### Scenario: Targets present — rebalance
- **WHEN** screening returns `N` targets and portfolio holds different ETFs
- **THEN** system MUST return sells for held ETFs not in targets (excluding defensive ETF) and buys sized equally across targets

#### Scenario: Equal-weight sizing
- **WHEN** `total_value = X` and `N` targets exist
- **THEN** each target SHALL be sized to `X / N` (rounded down to nearest 100 shares)
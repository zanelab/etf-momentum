## ADDED Requirements

### Requirement: Portfolio view
The system SHALL expose `GET /api/portfolio` returning current holdings with shares, average cost, last price, market value, and unrealized P&L.

#### Scenario: Mock portfolio on startup
- **WHEN** no real portfolio exists (initial state)
- **THEN** system MUST return a documented mock portfolio (e.g., 3 ETFs with plausible cost basis)

#### Scenario: Compute market value and P&L
- **WHEN** portfolio is requested
- **THEN** for each holding the system MUST return `market_value = shares × last_price` and `unrealized_pnl = (last_price - avg_cost) × shares`
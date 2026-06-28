## ADDED Requirements

### Requirement: Backtest engine
The system SHALL provide a backtest service that replays the screening engine day-by-day over a historical interval using fixture data, and SHALL persist task state to disk.

#### Scenario: Submit backtest
- **WHEN** client calls `POST /api/backtest` with `{ start_date, end_date, initial_cash, config_snapshot_id? }`
- **THEN** system MUST create a task record, return `{ task_id, status: "pending" }` immediately, and start a BackgroundTask

#### Scenario: Query task status
- **WHEN** client calls `GET /api/backtest/{task_id}`
- **THEN** system MUST return current status (`pending` | `running` | `done` | `failed`) and result if `done`

#### Scenario: Backtest output stats
- **WHEN** a backtest task completes successfully
- **THEN** system MUST return NAV series, full trade list, and aggregate stats: `total_return`, `annual_return`, `max_drawdown`, `sharpe`, `trade_count`

#### Scenario: Backtest interval limited to 1 year
- **WHEN** request interval > 365 days
- **THEN** system MUST reject with HTTP 400 and a clear error message
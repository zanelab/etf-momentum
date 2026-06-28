# Spec: bootstrap-fullstack

> OpenSpec 格式：`### Requirement` + `#### Scenario` (4 hashtags)。
> 本文档同时作为 OpenSpec CLI 校验入口与 speccoding gate 检查对象。
> 详细按能力拆分的版本见 `specs/<capability>/spec.md`。

## ADDED Requirements

### Requirement: Configuration persistence
The system SHALL persist three configuration entities — static ETF pool, theme keyword dictionary, and strategy parameters — to a local SQLite database, and SHALL expose REST CRUD endpoints for each.

#### Scenario: Read static pool
- **WHEN** client calls `GET /api/configs/pool`
- **THEN** system returns the list of all static pool entries with `code`, `display_name`, `enabled` fields

#### Scenario: Replace static pool
- **WHEN** client calls `POST /api/configs/pool` with a complete list of ETF codes
- **THEN** system replaces the entire static pool atomically and returns the updated list

#### Scenario: Update single pool entry
- **WHEN** client calls `PUT /api/configs/pool/{code}` with `{ "enabled": false }`
- **THEN** system updates only the `enabled` field of that entry

#### Scenario: Read theme dictionary
- **WHEN** client calls `GET /api/configs/themes`
- **THEN** system returns the theme dictionary as `{ "theme_name": ["keyword1", "keyword2"], ... }`

#### Scenario: Replace theme dictionary
- **WHEN** client calls `PUT /api/configs/themes` with a full dictionary
- **THEN** system replaces all theme keywords atomically

#### Scenario: Read strategy parameters
- **WHEN** client calls `GET /api/configs/strategy`
- **THEN** system returns all strategy parameters as a JSON object

#### Scenario: Update strategy parameters
- **WHEN** client calls `PUT /api/configs/strategy` with a partial parameter object
- **THEN** system merges the new values into existing parameters and persists

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

### Requirement: Portfolio view
The system SHALL expose `GET /api/portfolio` returning current holdings with shares, average cost, last price, market value, and unrealized P&L.

#### Scenario: Mock portfolio on startup
- **WHEN** no real portfolio exists (initial state)
- **THEN** system MUST return a documented mock portfolio (e.g., 3 ETFs with plausible cost basis)

#### Scenario: Compute market value and P&L
- **WHEN** portfolio is requested
- **THEN** for each holding the system MUST return `market_value = shares × last_price` and `unrealized_pnl = (last_price - avg_cost) × shares`

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

### Requirement: Market data source abstraction
The system SHALL define a `MarketDataSource` protocol with `history()`, `snapshot()`, and `all_etfs()` methods, and SHALL provide a `FixtureCSVSource` implementation reading from `backend/data/fixtures/*.csv`.

#### Scenario: Read history from fixture CSV
- **WHEN** `history(code, start, end, fields)` is called with a code that has a fixture file
- **THEN** system MUST return a `pandas.DataFrame` with the requested fields, filtered to the date range

#### Scenario: Missing fixture
- **WHEN** `history(code, ...)` is called for a code without a fixture file
- **THEN** system MUST raise `DataNotFoundError`; the API layer MUST convert this to HTTP 404 with a descriptive message

### Requirement: React frontend with config UI
The system SHALL provide a React (Vite + TypeScript) frontend with shadcn/ui components and TanStack Query, exposing pages for pool/theme/strategy configuration, signal display, portfolio view, backtest, and history.

#### Scenario: Frontend boots and proxies to backend
- **WHEN** developer runs `npm run dev` in `frontend/`
- **THEN** the dev server MUST start on port 5173 and proxy `/api/*` requests to the backend on port 8000

#### Scenario: Pool config page edits static pool
- **WHEN** user adds/removes a code or toggles `enabled` in PoolConfig page
- **THEN** UI MUST call `POST/PUT/DELETE /api/configs/pool` and refresh the table on success

#### Scenario: Signals page polls
- **WHEN** Signals page is open
- **THEN** it MUST poll `GET /api/signals/today` every 5 seconds and update on data change

#### Scenario: Backtest page polls task
- **WHEN** user submits a backtest
- **THEN** UI MUST poll `GET /api/backtest/{task_id}` every 2 seconds until status is `done` or `failed`

### Requirement: Migration parity
The system MUST preserve the original `main.py` for reference and MUST verify the migrated screening logic produces identical results for a set of fixture inputs.

#### Scenario: Parity test passes
- **WHEN** CI runs the parity test with 3 fixture inputs
- **THEN** the new implementation MUST produce byte-identical target lists to running the original `main.py` filter on the same inputs (when wrapped with shim adapters)

#### Scenario: main.py retained with deprecation notice
- **WHEN** developer reads `main.py`
- **THEN** the file header MUST clearly state "MIGRATED — see `backend/app/services/screening.py`. Retained for reference."

## MODIFIED Requirements

无（原项目无既有规格）

## REMOVED Requirements

无
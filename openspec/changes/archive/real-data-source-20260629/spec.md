# Spec: real-data-source

## ADDED Requirements

### Requirement: AkShare real-time market data source

The system SHALL provide an `AkShareSource` implementation of `MarketDataSource` that retrieves A-share ETF daily OHLCV bars from akshare's `fund_etf_hist_em` and the full ETF universe from `fund_etf_name_em`.

#### Scenario: Read OHLCV history for one ETF

- **WHEN** `history(code, start, end, fields)` is called on `AkShareSource` with a valid ETF code
- **THEN** system MUST call akshare's `fund_etf_hist_em` and return a `pandas.DataFrame` indexed by date with the requested fields
- **AND** akshare's `日期/开盘/收盘/最高/最低/成交量/成交额` columns MUST be mapped to `date/open/close/high/low/volume/money`

#### Scenario: Snapshot for a trading day

- **WHEN** `snapshot(code, as_of)` is called
- **THEN** system MUST return the last available bar at or before `as_of` as a dict with keys `last_price`, `volume`, `money`

#### Scenario: List all ETFs

- **WHEN** `all_etfs(as_of)` is called
- **THEN** system MUST call akshare's `fund_etf_name_em` and return a list of ETF codes currently listed

#### Scenario: akshare not installed

- **WHEN** the `akshare` package is not importable
- **THEN** `AkShareSource.__init__` MUST raise an `ImportError` with a message instructing the user to `pip install akshare`
- **AND** the rest of the system MUST continue to function on `fixture` source

### Requirement: Read-through cache for market data

The system SHALL provide a `CachedSource` decorator wrapping any `MarketDataSource` that caches bar data in a SQLite table `market_bar_cache` keyed by `(code, date)`.

#### Scenario: Cache hit

- **WHEN** `snapshot(code, as_of)` is called and `(code, as_of.date())` exists in `market_bar_cache`
- **THEN** system MUST return the cached row without calling the inner source
- **AND** the hit counter MUST increment by 1

#### Scenario: Cache miss

- **WHEN** `snapshot(code, as_of)` is called and `(code, as_of.date())` does NOT exist in cache
- **THEN** system MUST call `inner.snapshot(code, as_of)`, write the result to `market_bar_cache`, and return it
- **AND** the miss counter MUST increment by 1

#### Scenario: History partial miss

- **WHEN** `history(code, start, end)` is called and some dates in `[start, end]` are cached but others are not
- **THEN** system MUST return cached rows for cached dates and fetch only missing dates from inner source

#### Scenario: Cache stats endpoint

- **WHEN** `stats()` is called on `CachedSource`
- **THEN** system MUST return `{"hit": int, "miss": int}` accumulated since instance creation

### Requirement: Resilience: retry with exponential backoff and fixture fallback

The system SHALL wrap all akshare calls with `retry_with_backoff(fn, max_retries=3, backoff_factor=2.0, initial_delay=1.0)`. When all retries are exhausted AND a fallback source is configured, system MUST return data from the fallback.

#### Scenario: Transient failure recovers on retry

- **WHEN** akshare raises a transient error (network, timeout) on the first call
- **AND** the second attempt succeeds
- **THEN** system MUST return the successful result without surfacing the error

#### Scenario: All retries exhausted with fallback

- **WHEN** akshare fails all 3 retry attempts
- **AND** `AkShareSource` was constructed with `fixtures_dir`
- **THEN** system MUST delegate the call to `FixtureCSVSource` and return its result
- **AND** no error MUST be raised to the caller

#### Scenario: All retries exhausted without fallback

- **WHEN** akshare fails all 3 retry attempts
- **AND** `AkShareSource` was constructed WITHOUT `fixtures_dir`
- **THEN** system MUST raise the last exception

### Requirement: Source selector with environment variable and per-request override

The system SHALL provide a `make_source(name=None)` factory that returns a `MarketDataSource`. When `name` is `None`, system SHALL read the `ETF_DATA_SOURCE` environment variable (default: `"fixture"`).

#### Scenario: Default source from environment variable

- **WHEN** `make_source()` is called with `name=None`
- **AND** `ETF_DATA_SOURCE` is not set or set to `"fixture"`
- **THEN** system MUST return a `FixtureCSVSource` instance

#### Scenario: akshare selected via environment variable

- **WHEN** `make_source()` is called with `name=None`
- **AND** `ETF_DATA_SOURCE` is set to `"akshare"`
- **THEN** system MUST return a `CachedSource(AkShareSource(...))` instance

#### Scenario: Per-request override

- **WHEN** `make_source("akshare")` is called regardless of `ETF_DATA_SOURCE`
- **THEN** system MUST return the akshare-cached source

#### Scenario: Unknown source name

- **WHEN** `make_source("unknown")` is called
- **THEN** system MUST raise `ValueError` with a message listing valid options

### Requirement: Dynamic ETF pool with persistence and enable/disable

The system SHALL persist the full ETF universe from akshare in a `DynamicPoolEntry` SQLModel table with columns `code`, `name`, `is_enabled`, `last_synced_at`. System SHALL provide endpoints to sync, list, and toggle entries.

#### Scenario: Sync dynamic pool

- **WHEN** `POST /api/configs/pool/dynamic/sync` is called
- **THEN** system MUST call akshare's `fund_etf_name_em`, UPSERT each `(code, name)` row into `dynamic_pool_entry`, preserve `is_enabled` for existing rows, update `last_synced_at`, and return `{synced: N, total: M, enabled: K}`

#### Scenario: List dynamic pool

- **WHEN** `GET /api/configs/pool/dynamic` is called
- **THEN** system MUST return all rows from `dynamic_pool_entry` ordered by `code`

#### Scenario: Toggle enable flag

- **WHEN** `PATCH /api/configs/pool/dynamic/{code}` is called with `{"is_enabled": true}`
- **THEN** system MUST update that row's `is_enabled` and return the updated entry
- **AND** if the code does not exist, system MUST return 404

#### Scenario: filter_etfs merges static and dynamic pools

- **WHEN** `filter_etfs` is called with `dynamic_pool=[c for c in dynamic_pool_entry if is_enabled]`
- **THEN** system MUST treat the union of static + dynamic pools as the candidate set
- **AND** the deduplication rule SHALL remove duplicates

### Requirement: API endpoints source override and cache observability

The market data and screening API endpoints SHALL accept a `source` query parameter that overrides the default source for that request, and SHALL expose cache statistics when the active source is `CachedSource`.

#### Scenario: API source override

- **WHEN** `GET /api/market/history?code=X&start=Y&end=Z&source=akshare` is called
- **THEN** system MUST use `akshare` source for this request, regardless of `ETF_DATA_SOURCE`

#### Scenario: API cache stats

- **WHEN** `GET /api/health?stats=1` is called and the active source is `CachedSource`
- **THEN** system MUST include `cache_hit`, `cache_miss` fields in the response

### Requirement: Frontend DataSource page

The frontend SHALL provide a `/datasource` route rendering a `DataSource.tsx` page that displays the active source, last sync time, cache statistics, and a button to trigger dynamic-pool sync.

#### Scenario: Display active source

- **WHEN** user navigates to `/datasource`
- **THEN** page MUST show the current source name (`fixture` or `akshare`) and last sync timestamp from `/api/health`

#### Scenario: Show cache stats when on akshare

- **WHEN** the active source is `akshare`
- **THEN** page MUST show `hit_count`, `miss_count`, and computed hit-rate percentage from `/api/health?stats=1`

#### Scenario: Trigger sync

- **WHEN** user clicks the "立即同步" button
- **THEN** page MUST call `POST /api/configs/pool/dynamic/sync` and display the result `{synced, total, enabled}`

#### Scenario: Toggle dynamic pool entry

- **WHEN** user clicks an entry's checkbox in the dynamic-pool table
- **THEN** page MUST call `PATCH /api/configs/pool/dynamic/{code}` with the new `is_enabled` value

## MODIFIED Requirements

None (this change is purely additive).

## REMOVED Requirements

None.

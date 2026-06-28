## ADDED Requirements

### Requirement: Market data source abstraction
The system SHALL define a `MarketDataSource` protocol with `history()`, `snapshot()`, and `all_etfs()` methods, and SHALL provide a `FixtureCSVSource` implementation reading from `backend/data/fixtures/*.csv`.

#### Scenario: Read history from fixture CSV
- **WHEN** `history(code, start, end, fields)` is called with a code that has a fixture file
- **THEN** system MUST return a `pandas.DataFrame` with the requested fields, filtered to the date range

#### Scenario: Missing fixture
- **WHEN** `history(code, ...)` is called for a code without a fixture file
- **THEN** system MUST raise `DataNotFoundError`; the API layer MUST convert this to HTTP 404 with a descriptive message
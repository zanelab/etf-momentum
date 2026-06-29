# Spec: akshare-code-normalization

## ADDED Requirements

### Requirement: ETF code normalization to canonical form

The system SHALL provide a `normalize_etf_code(code: str) -> str` utility that returns the canonical form `XXXXXX.XSHG` or `XXXXXX.XSHE` for every valid ETF code. The system SHALL also provide `same_etf(a, b) -> bool` returning whether two codes normalize to the same string.

#### Scenario: Normalize bare 6-digit code (Shanghai)

- **WHEN** `normalize_etf_code("510300")` is called
- **THEN** system MUST return `"510300.XSHG"`

#### Scenario: Normalize bare 6-digit code (Shenzhen)

- **WHEN** `normalize_etf_code("159915")` is called
- **THEN** system MUST return `"159915.XSHE"`

#### Scenario: Idempotent on canonical input

- **WHEN** `normalize_etf_code("510300.XSHG")` is called
- **THEN** system MUST return `"510300.XSHG"` unchanged

#### Scenario: Strip whitespace and uppercase

- **WHEN** `normalize_etf_code("  510300.xshg  ")` is called
- **THEN** system MUST return `"510300.XSHG"`

#### Scenario: Reject malformed input

- **WHEN** `normalize_etf_code("abc")` is called
- **THEN** system MUST raise `ValueError`

#### Scenario: same_etf equivalence across formats

- **WHEN** `same_etf("510300", "510300.XSHG")` is called
- **THEN** system MUST return `True`

#### Scenario: same_etf inequality

- **WHEN** `same_etf("510300.XSHG", "159915.XSHE")` is called
- **THEN** system MUST return `False`

### Requirement: akshare source returns normalized codes

The `AkShareSource.all_etf_entries(as_of)` method SHALL return code strings normalized via `normalize_etf_code()` so that callers receive canonical-form codes regardless of akshare's raw output.

#### Scenario: Raw akshare codes are normalized

- **WHEN** akshare's `fund_etf_spot_em()` returns rows with codes like `"510300"` and `"159915"`
- **AND** `AkShareSource.all_etf_entries(as_of)` is called
- **THEN** system MUST return `(code, name)` pairs where every `code` is in canonical form (`"510300.XSHG"`, `"159915.XSHE"`)

### Requirement: Pool fusion deduplicates across code formats

The `filter_etfs` function SHALL treat codes as equivalent when `same_etf(a, b)` is true, so static-pool (canonical form) and dynamic-pool (originally bare from akshare) entries for the same ETF are merged into a single candidate.

#### Scenario: Static + dynamic deduplication

- **WHEN** `filter_etfs` is called with `static_pool=["510300.XSHG"]` and `dynamic_pool=["510300"]`
- **THEN** the fused pool MUST contain `510300.XSHG` exactly once (not twice)

#### Scenario: Defensive ETF exclusion handles bare code

- **WHEN** `filter_etfs` is called with `params.defensive_etf = "511880"` (bare code)
- **AND** the pool contains `"511880.XSHG"`
- **THEN** the defensive ETF MUST be excluded from the candidate pool

### Requirement: load_display_names falls back to canonical-form lookup

The `load_display_names(codes)` function in `backend/app/services/today.py` SHALL return a `{code: display_name}` map that includes canonical-form keys, by falling back to a normalized lookup when an exact-match query misses.

#### Scenario: Bare-code input resolves to canonical display name

- **WHEN** `load_display_names(["510300"])` is called
- **AND** the `static_pool` table contains a row `code="510300.XSHG"` with `display_name="沪深300ETF"`
- **THEN** system MUST return `{"510300": "沪深300ETF"}` (key is the input code; value is the matched display name)

#### Scenario: Canonical-form input resolves directly

- **WHEN** `load_display_names(["510300.XSHG"])` is called
- **AND** the `static_pool` table contains a row `code="510300.XSHG"` with `display_name="沪深300ETF"`
- **THEN** system MUST return `{"510300.XSHG": "沪深300ETF"}`

#### Scenario: Mixed format input all resolve

- **WHEN** `load_display_names(["510300", "510500.XSHG"])` is called
- **AND** both rows exist in `static_pool`
- **THEN** system MUST return `{"510300": "...", "510500.XSHG": "..."}` with both display names filled

### Requirement: Dynamic pool sync upsert key is normalized

The `POST /api/configs/pool/dynamic/sync` endpoint SHALL use `normalize_etf_code(code)` as the upsert key when matching existing `DynamicPoolEntry` rows, so that bare-code and canonical-form variants of the same ETF are never stored as two separate rows.

#### Scenario: Sync deduplicates across format drift

- **WHEN** the `dynamic_pool_entry` table already contains a row with `code="510300"` (legacy bare code from a prior sync)
- **AND** `POST /api/configs/pool/dynamic/sync` runs and akshare returns `"510300"`
- **THEN** system MUST upsert the existing row (in-place update of name and `last_synced_at`), preserving `is_enabled`
- **AND** MUST NOT create a new row `code="510300.XSHG"`

## MODIFIED Requirements

None — the change is purely additive: existing call sites still work, new behavior is opt-in by code path.

## REMOVED Requirements

None.
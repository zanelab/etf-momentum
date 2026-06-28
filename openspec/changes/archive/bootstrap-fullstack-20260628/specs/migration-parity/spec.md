## ADDED Requirements

### Requirement: Migration parity
The system MUST preserve the original `main.py` for reference and MUST verify the migrated screening logic produces identical results for a set of fixture inputs.

#### Scenario: Parity test passes
- **WHEN** CI runs the parity test with 3 fixture inputs
- **THEN** the new implementation MUST produce byte-identical target lists to running the original `main.py` filter on the same inputs (when wrapped with shim adapters)

#### Scenario: main.py retained with deprecation notice
- **WHEN** developer reads `main.py`
- **THEN** the file header MUST clearly state "MIGRATED — see `backend/app/services/screening.py`. Retained for reference."
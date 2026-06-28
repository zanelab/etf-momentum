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
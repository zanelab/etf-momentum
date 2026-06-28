## ADDED Requirements

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
## ADDED Requirements

### Requirement: Dashboard 路由与默认重定向
The system SHALL expose a `/dashboard` route that renders the momentum ranking view, and SHALL redirect the index route `/` to `/dashboard` by default. The existing `/health` route MUST remain reachable.

#### Scenario: User opens the app
- **WHEN** the user navigates to `/`
- **THEN** the browser is redirected to `/dashboard`
- **AND** the momentum ranking view is rendered

#### Scenario: User navigates to health page
- **WHEN** the user clicks the "健康检查" sidebar item or navigates to `/health`
- **THEN** the HealthPage is rendered

### Requirement: 数据加载与展示
The system SHALL fetch `GET /api/v1/signals/latest` and `GET /api/v1/etfs?limit=500` in parallel when the dashboard mounts, and SHALL render the snapshot's date, the total ETF count, and the per-action counts (BUY/HOLD/WATCH) in summary cards above the ranking table.

#### Scenario: Successful load with non-empty snapshot
- **WHEN** the dashboard mounts AND the latest signals snapshot contains at least one row
- **THEN** summary cards display the snapshot date, total ETF count, and BUY/HOLD/WATCH counts
- **AND** the ranking table displays one row per signal, joined with the ETF dictionary on `etf_code`

#### Scenario: Signals endpoint fails
- **WHEN** the dashboard mounts AND `GET /api/v1/signals/latest` returns a non-2xx response
- **THEN** a full-width error card is rendered with the error message
- **AND** the table is not rendered

#### Scenario: ETF dictionary endpoint fails
- **WHEN** the dashboard mounts AND `GET /api/v1/etfs` returns a non-2xx response BUT signals succeeds
- **THEN** the ranking table is still rendered
- **AND** rows display `etf_code` only with `name` and `category` shown as `—`

#### Scenario: Empty snapshot
- **WHEN** the dashboard mounts AND the latest signals snapshot contains zero rows
- **THEN** an explicit empty-state card is rendered instructing the user to run the realtime-signals CLI

### Requirement: 排名表格布局
The system SHALL render rows in two sections: a top "BUY" section containing all rows with `action === "BUY"`, and a bottom "其它" section containing HOLD, WATCH, and rows with a null/unknown action. Within each section, rows SHALL be ordered by `rank ASC NULLS LAST, etf_code ASC` (matching the backend default).

#### Scenario: BUY section appears above others
- **WHEN** the snapshot contains rows with mixed actions (BUY, HOLD, WATCH)
- **THEN** BUY rows appear in the top section
- **AND** HOLD/WATCH/null rows appear in the bottom section

#### Scenario: Rank null handling
- **WHEN** a row has `rank === null`
- **THEN** the row is sorted to the end of its section

### Requirement: Action 徽章颜色编码
The system SHALL render the `action` column as a colored badge. BUY SHALL be green, HOLD SHALL be blue, WATCH SHALL be gray. Any unknown action value SHALL be rendered in gray with the raw text label.

#### Scenario: Known action values
- **WHEN** a row has `action === "BUY"`
- **THEN** the badge uses the green palette
- **WHEN** a row has `action === "HOLD"`
- **THEN** the badge uses the blue palette
- **WHEN** a row has `action === "WATCH"`
- **THEN** the badge uses the gray palette

#### Scenario: Unknown action value
- **WHEN** a row has an action value outside the {BUY, HOLD, WATCH} set
- **THEN** the badge uses the gray palette
- **AND** the original text is shown verbatim

### Requirement: 数值字段渲染
The system SHALL render `momentum_score` (a string-serialized Decimal from the backend, possibly null) as a fixed-precision number with 4 significant digits. Null scores SHALL render as `—`.

#### Scenario: Score is present
- **WHEN** a row has `momentum_score === "0.123456"`
- **THEN** the cell displays `0.1235`

#### Scenario: Score is null
- **WHEN** a row has `momentum_score === null`
- **THEN** the cell displays `—`

### Requirement: 状态机一致性
The system SHALL follow the existing `idle | loading | ok | error` state machine pattern used by `useHealthStore` for both the signals and ETF-dictionary stores.

#### Scenario: Initial load lifecycle
- **WHEN** the dashboard mounts
- **THEN** the signals store transitions `idle → loading → (ok | error)`
- **AND** the ETF-dictionary store transitions `idle → loading → (ok | error)`
- **AND** the page does not render the table until both stores leave `loading`

### Requirement: 侧边栏导航
The system SHALL display a "动量看板" sidebar link in the Layout that routes to `/dashboard`, in addition to the existing "健康检查" link.

#### Scenario: Sidebar entry present
- **WHEN** the Layout is rendered
- **THEN** the sidebar contains two links: "动量看板" (→ /dashboard) and "健康检查" (→ /health)
- **AND** the link matching the current route is visually highlighted

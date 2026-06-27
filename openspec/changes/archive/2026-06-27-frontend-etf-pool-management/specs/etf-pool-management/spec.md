## ADDED Requirements

### Requirement: 路由与导航
The system SHALL expose a `/pools` route that renders the pool management UI, and SHALL add a "策略池" sidebar link in the Layout that routes to it.

#### Scenario: User navigates to /pools
- **WHEN** the user clicks the "策略池" sidebar item or navigates to `/pools`
- **THEN** the PoolsPage is rendered
- **AND** the sidebar link matching the current route is visually highlighted

### Requirement: 池列表展示
The system SHALL fetch `GET /api/v1/pools` on mount and render the returned pools as a card grid showing name, member count, description (truncated to 2 lines), created/updated timestamps, and per-card action buttons (edit, delete).

#### Scenario: Pool list loads successfully
- **WHEN** the PoolsPage mounts AND `/pools` returns a list
- **THEN** one card per pool is rendered with name + member count + description preview + timestamps

#### Scenario: Pool list is empty
- **WHEN** the user has zero pools
- **THEN** the page shows an empty state with a "新建策略池" CTA button

#### Scenario: Pool list fails to load
- **WHEN** the PoolsPage mounts AND `/pools` returns non-2xx
- **THEN** the page shows a "池列表加载失败" error card with a retry button

### Requirement: 创建策略池
The system SHALL allow the user to create a new pool via `POST /api/v1/pools` with body `{name, description?, etf_codes: string[]}`. The name SHALL be required and unique (case-sensitive). The system SHALL reject duplicate names with HTTP 409.

#### Scenario: Successful creation
- **WHEN** the user enters a unique name + selects 2+ ETFs + clicks "保存"
- **THEN** the system posts to `/api/v1/pools`
- **AND** the new pool appears at the top of the list
- **AND** the editor collapses back to list view

#### Scenario: Empty name is blocked client-side
- **WHEN** the user attempts to save without a name
- **THEN** no API call is made
- **AND** the name field shows "请填写名称"

#### Scenario: Empty etf_codes is blocked client-side
- **WHEN** the user attempts to save with zero ETFs selected
- **THEN** no API call is made
- **AND** the ETF picker shows "请至少选择一只 ETF"

#### Scenario: Duplicate name returns 409
- **WHEN** the user submits a name that already exists
- **THEN** the system shows "已存在同名策略池" next to the name field
- **AND** the form remains editable

#### Scenario: Server validation error on etf_codes
- **WHEN** the server returns 422 (e.g., one code is not in etfs table)
- **THEN** the system displays the backend detail message under the picker

### Requirement: 编辑策略池
The system SHALL allow the user to edit an existing pool via `PUT /api/v1/pools/{id}` with body `{name, description?, etf_codes: string[]}`. The PUT SHALL be a full replacement of the members list (not a patch). The system SHALL display a diff summary ("将保存 N 只 ETF（原 M 只）") before submission when the count changes.

#### Scenario: Successful update
- **WHEN** the user edits a pool's name + members + clicks "保存"
- **THEN** the system calls `PUT /api/v1/pools/{id}`
- **AND** the pool card in the list reflects the new name + member count

#### Scenario: Member count shrinks visibly
- **WHEN** the user removes an ETF from a pool that originally had 5 members
- **THEN** the diff summary shows "将保存 4 只 ETF（原 5 只）"
- **AND** the removed ETF is visually marked in the picker

#### Scenario: Optimistic locking via 409 on rename
- **WHEN** the user renames a pool to a name already taken by another pool
- **THEN** the system shows "已存在同名策略池" under the name field

### Requirement: 删除策略池
The system SHALL allow the user to delete a pool via `DELETE /api/v1/pools/{id}`. The system SHALL prompt for confirmation with a native `window.confirm()` dialog before submitting.

#### Scenario: User confirms deletion
- **WHEN** the user clicks "删除" and confirms the native dialog
- **THEN** the system calls `DELETE /api/v1/pools/{id}`
- **AND** the pool card is removed from the list
- **AND** no success toast is shown (immediate removal is the feedback)

#### Scenario: User cancels deletion
- **WHEN** the user clicks "删除" and cancels the native dialog
- **THEN** no API call is made
- **AND** the pool remains in the list unchanged

#### Scenario: Server returns 404 on delete
- **WHEN** the pool was already deleted (race condition)
- **THEN** the system silently removes the card from the list
- **AND** no error is shown

### Requirement: 数据模型
The system SHALL persist pools in two tables: `etf_pools` (id, name UNIQUE, description, created_at, updated_at) and `etf_pool_members` (pool_id FK, etf_code FK, position INT, PRIMARY KEY (pool_id, etf_code)). The `name` column SHALL have a UNIQUE constraint. All `etf_code` values SHALL exist in the `etfs` table (enforced by the application layer since SQLite FK enforcement is pragma-dependent).

#### Scenario: Creating a pool writes both rows
- **WHEN** the user creates a pool with 3 ETFs
- **THEN** exactly 1 row is inserted into `etf_pools`
- **AND** exactly 3 rows are inserted into `etf_pool_members`
- **AND** the transaction commits atomically

#### Scenario: Updating a pool replaces the members
- **WHEN** the user edits a pool from 5 members to 2 members
- **THEN** `etf_pool_members` rows for that pool go from 5 to 2
- **AND** the `etf_pools.updated_at` is refreshed

### Requirement: 池编辑器的 ETF 选择器
The system SHALL reuse the same checkbox-grid picker as the BacktestForm: search filter + paginated "show 12 / all" + "已选 N / total" header. The picker SHALL be embedded inline in the PoolEditor (not in a modal).

#### Scenario: User searches for an ETF
- **WHEN** the user types "沪深" in the search box
- **THEN** the grid filters to ETFs whose name or code matches

#### Scenario: User toggles ETF selection
- **WHEN** the user toggles a checkbox
- **THEN** the header count updates immediately

### Requirement: 编辑器状态管理
The system SHALL keep the editor state local (component useState) — no global store for the in-progress edit. The pools-store SHALL only hold the list, the currently-fetched pool detail, and submission status. Canceling an edit SHALL discard local state without touching the store.

#### Scenario: User cancels an edit
- **WHEN** the user clicks "取消" mid-edit
- **THEN** the in-progress form is discarded
- **AND** the pools-store is untouched
- **AND** the list view is restored

#### Scenario: User saves an edit
- **WHEN** the user clicks "保存" with valid changes
- **THEN** the in-progress form is committed via PUT
- **AND** the store's list is refreshed to reflect the new state

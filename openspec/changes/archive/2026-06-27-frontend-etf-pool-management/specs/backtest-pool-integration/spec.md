## ADDED Requirements

### Requirement: BacktestForm 池选择模式
The system SHALL add a mode selector at the top of the BacktestForm with two options: "使用策略池" and "自定义". In "使用策略池" mode the ETF checkboxes SHALL be locked (disabled) and populated from a chosen pool. In "自定义" mode the existing free-form checkbox interaction is preserved.

#### Scenario: User switches to pool mode
- **WHEN** the user selects "使用策略池" from the mode selector
- **THEN** a pool dropdown appears
- **AND** the ETF checkboxes become disabled (visually distinct)
- **AND** previously-selected free-form checkboxes are preserved in local state but not visible

#### Scenario: User picks a pool
- **WHEN** the user selects a pool from the dropdown in pool mode
- **THEN** the system calls `GET /api/v1/pools/{id}` (or uses the cached list's detail if already loaded)
- **AND** all members of the pool appear as checked (and disabled) checkboxes

#### Scenario: User switches back to custom mode
- **WHEN** the user selects "自定义" from the mode selector
- **THEN** the checkboxes become enabled
- **AND** the previously-selected free-form checkboxes are restored
- **AND** the pool dropdown is hidden

#### Scenario: Switching to pool mode with active selections prompts for confirmation
- **WHEN** the user is in custom mode with N≥1 ETFs selected AND switches to pool mode
- **THEN** the system shows `window.confirm("将丢弃当前 X 个自定义勾选，确定？")`
- **AND** on cancel, the mode stays at "自定义"
- **AND** on confirm, the mode switches and the selections are preserved in local state for round-trip

### Requirement: 池列表为空时的回退
The system SHALL handle the case where the pools list is empty (or fails to load) inside the BacktestForm's pool mode without breaking the rest of the form.

#### Scenario: Pools list is empty
- **WHEN** the user enters pool mode AND `GET /api/v1/pools` returns 0 items
- **THEN** the pool dropdown shows "（暂无策略池）"
- **AND** a "前往创建" link is shown that routes to `/pools`

#### Scenario: Pools list fails to load
- **WHEN** the user enters pool mode AND `GET /api/v1/pools` returns non-2xx
- **THEN** the pool dropdown shows "加载失败" with a retry button
- **AND** the rest of the form remains functional in custom mode

### Requirement: 提交时携带池 id（可选）
The system MAY include an optional `pool_id` field in the BacktestRequest body when submitting in pool mode. The backend SHALL treat `pool_id` as informational only (the request still uses `etf_pool` codes).

#### Scenario: Submit in pool mode
- **WHEN** the user submits the form in pool mode with a chosen pool
- **THEN** the request body includes both `etf_pool: [...codes...]` AND `pool_id: <id>`
- **AND** the backend stores the pool_id on the BacktestRun row for future reference

#### Scenario: Submit in custom mode
- **WHEN** the user submits in custom mode
- **THEN** the request body omits `pool_id` (or sets it to null)

### Requirement: 模式与结果解耦
The system SHALL keep the pool-mode selector state independent of the backtest submission result. After a successful backtest, the mode selector SHALL retain its last value so the user can adjust parameters and re-run without re-selecting the pool.

#### Scenario: User submits and result appears
- **WHEN** a backtest completes successfully in pool mode
- **THEN** the form remains populated with the same mode + pool selection
- **AND** the result area updates with the new run + NAV chart

#### Scenario: User changes a parameter and re-submits
- **WHEN** the user adjusts lookback and re-submits in pool mode
- **THEN** the same pool is used (no need to re-select)

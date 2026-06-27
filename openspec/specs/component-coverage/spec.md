# Component Coverage — Button / HealthPage / Layout

> 本次变更的产品行为不变，仅在前端测试套件中显式锁定以下契约。这些 Requirement 定义了「在合并前必须通过的测试」。

## ADDED Requirements

### Requirement: Button forwards ref and merges className

The `Button` component (`components/ui/button.tsx`) MUST forward refs to the underlying `<button>` element and MUST merge a passed `className` with the variant-derived classes.

#### Scenario: ref forwarded
- **WHEN** a `ref` is attached to `<Button>`
- **THEN** the ref points to the rendered `<button>` DOM element

#### Scenario: className merged
- **WHEN** `<Button className="custom-class" />` is rendered
- **THEN** the resulting button contains both the variant classes and `custom-class`

### Requirement: Button respects disabled and onClick

The `Button` component MUST call `onClick` when clicked and MUST NOT call it when `disabled`.

#### Scenario: click invokes handler
- **WHEN** the button is clicked
- **THEN** the `onClick` handler is invoked exactly once

#### Scenario: disabled suppresses click
- **WHEN** the button has `disabled={true}` and is clicked
- **THEN** the `onClick` handler is NOT invoked

### Requirement: HealthPage shows correct UI per store status

The `HealthPage` component MUST render:
- A "重新检测" button when `status === "idle"` or `"ok"` or `"error"`.
- A disabled "检测中..." button (with loading state) when `status === "loading"`.
- The `data` JSON when `status === "ok"`.
- The `error` message when `status === "error"`.

#### Scenario: idle shows retry button
- **WHEN** the store is in `idle` state on mount
- **THEN** a "重新检测" button is shown and no data or error is displayed

#### Scenario: loading shows spinner state
- **WHEN** the store transitions to `loading`
- **THEN** the button label is "检测中..." and is disabled

#### Scenario: ok shows JSON data
- **WHEN** the store is in `ok` with `data = { status: "ok" }`
- **THEN** a `<pre>` block contains the JSON representation of the data

#### Scenario: error shows error message
- **WHEN** the store is in `error` with `error = "network down"`
- **THEN** the error message "network down" is displayed in an error-styled container

### Requirement: HealthPage invokes /health on mount and on retry

The `HealthPage` component MUST trigger a single `apiGet("/health")` call on mount, and MUST trigger another call when the user clicks the "重新检测" button.

#### Scenario: mount triggers API call
- **WHEN** HealthPage is mounted
- **THEN** `apiGet` is called once with `"/health"`

#### Scenario: retry triggers another API call
- **WHEN** the user clicks the "重新检测" button after the initial check
- **THEN** `apiGet` is called a second time

### Requirement: Layout renders all four NavLinks with active highlight

The `Layout` component MUST render four NavLinks (动量看板 / 策略池 / 回测 / 健康检查) and MUST mark the NavLink matching the current pathname with `aria-current="page"`.

#### Scenario: all four links rendered
- **WHEN** Layout is rendered
- **THEN** the four labels are visible in the nav

#### Scenario: matching link is active
- **WHEN** Layout is rendered with `initialEntries={["/pools"]}`
- **THEN** the 策略池 link has `aria-current="page"`

#### Scenario: non-matching link is not active
- **WHEN** Layout is rendered with `initialEntries={["/pools"]}`
- **THEN** the 动量看板 link does NOT have `aria-current="page"`

### Requirement: Layout renders Outlet with the child route

The `Layout` component MUST render its `Outlet` so that the routed page appears in the main content area.

#### Scenario: child route renders
- **WHEN** Layout is rendered with a child `<div data-testid="child">hello</div>` route
- **THEN** the child div appears in the output
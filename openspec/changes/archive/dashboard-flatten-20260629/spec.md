# Spec: dashboard-flatten

## ADDED Requirements

### Requirement: Dashboard renders the full weekly action checklist inline

The Dashboard page (`/`) SHALL render the complete content that previously lived on `/signals`, inline as one of its cards, with no drill-down to a separate route. Specifically, the Dashboard MUST render the weekly rebalance checklist including:

- A `今日调仓` heading with the `as_of` date
- An empty-state line `今天没有需要做的 ✓` when no signals exist
- A red SELL table with columns `代码 | 名称 | 当前持仓 | 卖出数量 | 估算金额` and one row per SELL signal
- A green BUY table with columns `代码 | 名称 | 目标金额 | 买入数量` and one row per BUY signal
- A global `📋 复制完整调仓清单` button in the page header that copies all actions in `卖出 X 1,000 份` / `买入 Y 1,300 份` format
- A per-row `📋 复制` button on each SELL and BUY row
- An amber defensive-mode banner when `signals` contains exactly one BUY whose reason is `DEFENSIVE_REASON`
- A collapsible `▶ 原始筛选输出` block showing the raw `/api/screening/today` JSON
- A collapsible `▶ 进阶：为什么这样选` block showing per-ETF `(代码 | 名称 | 动量分 | 年化收益 | R² | 量比)` from `/api/screening/today` `details` field

#### Scenario: Dashboard shows the sell table when SELL signals exist

- **WHEN** `/api/signals/today` returns one SELL signal `{type: SELL, code: 510500.XSHG, shares: 800}`
- **AND** the user visits `/`
- **THEN** the Dashboard MUST render the SELL table with one row showing `510500.XSHG` and `800 份`

#### Scenario: Dashboard shows the buy table when BUY signals exist

- **WHEN** `/api/signals/today` returns one BUY signal `{type: BUY, code: 510300.XSHG, target_value: 5095}`
- **AND** the user visits `/`
- **THEN** the Dashboard MUST render the BUY table with one row showing `510300.XSHG` and `¥5,095`

#### Scenario: Dashboard shows the defensive banner

- **WHEN** `/api/signals/today` returns one BUY signal with `reason: "无动量目标，切换防御模式"`
- **AND** the user visits `/`
- **THEN** the Dashboard MUST render the amber banner containing the text `防御模式`

#### Scenario: Dashboard shows the empty-state when no signals

- **WHEN** `/api/signals/today` returns `signals: []`
- **AND** the user visits `/`
- **THEN** the Dashboard MUST render the line `今天没有需要做的 ✓`

### Requirement: Dashboard renders the full portfolio holdings table inline

The Dashboard page (`/`) SHALL render the complete content that previously lived on `/portfolio`, inline as one of its cards. The Dashboard MUST render a holdings table for every entry in `/api/portfolio.holdings` (not a Top-5 subset) with columns `代码 | 名称 | 持仓数量 | 成本价 | 现价 | 市值 | 浮动盈亏`. When `holdings` is empty the card MUST render an empty-state line `暂无持仓`.

#### Scenario: Dashboard shows all holdings rows

- **WHEN** `/api/portfolio` returns `holdings: [{code: 510300.XSHG, shares: 1300, cost_price: 4.0, current_price: 4.2, market_value: 5460, pnl: 260}, ...]`
- **AND** the user visits `/`
- **THEN** the Dashboard MUST render one row per holding including all 7 columns

#### Scenario: Dashboard shows the empty holdings state

- **WHEN** `/api/portfolio` returns `holdings: []`
- **AND** the user visits `/`
- **THEN** the Dashboard MUST render `暂无持仓` in the 当前持仓 card

### Requirement: /signals, /portfolio, /screening routes are removed

The top-level `App` component MUST NOT register `<Route path="/signals" ...>`, `<Route path="/portfolio" ...>`, or `<Route path="/screening" ...>`. Visiting any of these URLs SHALL fall through to the existing wildcard route `<Route path="*" element={<Navigate to="/" replace />} />` and redirect to `/`.

#### Scenario: /signals redirects to / via wildcard

- **WHEN** the user navigates to `/signals`
- **THEN** the app MUST redirect to `/` and render the Dashboard

#### Scenario: /portfolio redirects to / via wildcard

- **WHEN** the user navigates to `/portfolio`
- **THEN** the app MUST redirect to `/` and render the Dashboard

#### Scenario: /screening redirects to / via wildcard

- **WHEN** the user navigates to `/screening`
- **THEN** the app MUST redirect to `/` and render the Dashboard

### Requirement: Top nav has exactly 2 entries

The `AppShell` component's top navigation MUST contain exactly two entries: `仪表盘` (linking to `/`) and `设置` (a button that opens the settings sidebar). The previous entries `持仓` (linking to `/portfolio`) and `今日调仓` (linking to `/signals`) MUST NOT appear in the top nav.

#### Scenario: Top nav shows exactly 2 entries

- **WHEN** the user visits `/`
- **THEN** the rendered top nav MUST contain exactly the strings `仪表盘` and `设置`
- **AND** MUST NOT contain `持仓` or `今日调仓`

### Requirement: Signals.tsx and Portfolio.tsx are deleted

The files `frontend/src/pages/Signals.tsx` and `frontend/src/pages/Portfolio.tsx` MUST be removed from the repository. Their content MUST be migrated into `frontend/src/pages/Dashboard.tsx`. The test file `frontend/src/pages/__tests__/Signals.test.tsx` MUST be removed (its assertions move to `Dashboard.flatten.test.tsx`). The test file `frontend/src/__tests__/screening-redirect.test.tsx` MUST be removed.

#### Scenario: Source tree has no Signals.tsx or Portfolio.tsx

- **WHEN** listing `frontend/src/pages/`
- **THEN** the result MUST NOT contain `Signals.tsx` or `Portfolio.tsx`

#### Scenario: Dashboard.tsx contains the migrated content

- **WHEN** reading `frontend/src/pages/Dashboard.tsx`
- **THEN** the file MUST contain rendering logic for the action checklist (SELL table, BUY table, defensive banner, copy buttons, expandable blocks)
- **AND** MUST contain rendering logic for the full holdings table
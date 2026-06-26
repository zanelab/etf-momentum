## ADDED Requirements

### Requirement: 路由与导航
The system SHALL expose a `/backtest` route that renders the backtest UI, and SHALL add a "回测" sidebar link in the Layout that routes to it.

#### Scenario: User navigates to /backtest
- **WHEN** the user clicks the "回测" sidebar item or navigates to `/backtest`
- **THEN** the BacktestPage is rendered
- **AND** the sidebar link matching the current route is visually highlighted

### Requirement: ETF 池选择器
The system SHALL fetch `GET /api/v1/etfs?limit=500` on mount and render the returned ETFs as a selectable grid of checkboxes. The user SHALL be able to select zero or more ETFs; the count of selected items SHALL be displayed live in the section header.

#### Scenario: ETF list loads successfully
- **WHEN** the BacktestPage mounts AND `/etfs?limit=500` returns a list
- **THEN** the ETF pool section renders one checkbox per ETF
- **AND** the header shows "已选 0 / N" (N = total ETFs)

#### Scenario: User selects an ETF
- **WHEN** the user toggles a checkbox
- **THEN** the count in the header updates immediately

#### Scenario: ETF list fails to load
- **WHEN** the BacktestPage mounts AND `/etfs?limit=500` returns non-2xx
- **THEN** the ETF pool section shows a "ETF 字典加载失败" error
- **AND** the submit button is disabled

### Requirement: 参数表单
The system SHALL render a form with the following fields, all controlled:
- start (date input, required)
- end (date input, required)
- initial_cash (number input, required, > 0)
- lookback (number input, default 252, > 0)
- skip (number input, default 21, >= 0)
- top_n (number input, default 5, > 0)
- rebalance_freq (select: monthly | quarterly, default monthly)

The form SHALL be disabled while a backtest submission is in flight.

#### Scenario: User fills in valid parameters
- **WHEN** the user enters all required fields with valid values
- **THEN** the submit button is enabled
- **AND** the form is not in error state

### Requirement: 客户端校验
The system SHALL perform client-side validation on submit and prevent the API call when any of the following hold: etf_pool is empty; start >= end; initial_cash <= 0; lookback < 1; skip < 0; top_n < 1.

#### Scenario: Empty pool
- **WHEN** the user submits with zero ETFs selected
- **THEN** no API call is made
- **AND** the ETF pool section shows "请至少选择一只 ETF"

#### Scenario: Invalid date range
- **WHEN** the user submits with start >= end
- **THEN** no API call is made
- **AND** the form shows a date-range error

### Requirement: 提交与状态机
The system SHALL submit the form to `POST /api/v1/backtest` with the body `{etf_pool, start, end, initial_cash, lookback, skip, top_n, rebalance_freq}`. The store SHALL transition through `idle → submitting → (ok | error)`. While `submitting`, the form SHALL be disabled and a spinner SHALL be shown.

#### Scenario: Successful submission
- **WHEN** the user submits a valid form
- **THEN** the store status becomes `submitting`
- **AND** after the response, the status becomes `ok`
- **AND** the response data (BacktestRun with id and metrics) is stored
- **AND** the system automatically fetches the NAV series for the returned id

#### Scenario: Server returns 422
- **WHEN** the user submits a form that passes client validation BUT the server returns 422
- **THEN** the store status becomes `error`
- **AND** the form extracts per-field errors from the response and displays them next to the relevant field
- **AND** the form remains editable

#### Scenario: Network error
- **WHEN** the API call throws (network / 5xx with no body)
- **THEN** the store status becomes `error`
- **AND** a full-width error card is shown with the error message

### Requirement: NAV 折线图
After a successful backtest, the system SHALL fetch `GET /api/v1/backtest/{id}/nav` and render the result as a responsive line chart with date on the X axis and NAV value on the Y axis.

#### Scenario: NAV data loads
- **WHEN** the NAV fetch succeeds
- **THEN** the chart renders one point per `{date, nav}` pair
- **AND** the X axis displays dates in YYYY-MM-DD format
- **AND** the Y axis displays NAV values with thousands separators
- **AND** the chart is responsive (adapts to container width)

#### Scenario: NAV fetch fails
- **WHEN** the NAV fetch fails
- **THEN** the metrics cards are still rendered
- **AND** the chart area shows a "NAV 数据加载失败" error

### Requirement: 业绩指标展示
The system SHALL render the 6 performance metrics from the backtest response in a card grid. Percentages (total_return, annualized_return, max_drawdown) SHALL be rendered with 2 decimal places followed by `%`. Ratios (sharpe, sortino, calmar) SHALL be rendered with 3 decimal places. Null values SHALL render as `—`.

#### Scenario: All metrics present
- **WHEN** the backtest response includes all 6 metrics
- **THEN** six cards display the values with the appropriate formatting

#### Scenario: Some metrics are null
- **WHEN** the response has a null value (e.g. calmar when max_drawdown is 0)
- **THEN** that card displays `—`

### Requirement: 表单不自动重置
After a successful backtest, the form SHALL remain populated with the last submitted values, allowing the user to adjust parameters and re-run.

#### Scenario: User adjusts and re-submits
- **WHEN** a backtest has completed successfully
- **THEN** the form fields retain their values
- **AND** the result area updates when the new submission completes

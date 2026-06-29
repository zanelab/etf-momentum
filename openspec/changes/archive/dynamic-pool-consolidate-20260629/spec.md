# Spec: dynamic-pool-consolidate

## ADDED Requirements

### Requirement: 动态池主页承载两个同步操作与同步状态可观测

`/dynamic-pool` 页面 MUST 同时承载两个写操作——「同步 ETF」（`POST /api/configs/pool/dynamic/sync`）与「同步 ETF 历史数据」（`POST /api/sync/historical/trigger`）——并暴露 `static_pool ∪ dynamic_pool` 中每只 ETF 的历史同步状态。

**UI 行为**：
- 页面顶部右上方两个按钮：`同步 ETF`（主按钮，primary 样式）与 `同步 ETF 历史数据`（次按钮，secondary 样式）
- 任一同步操作 in-flight 时（MUST 由 `useSyncDynamicPool().isPending || useTriggerSync().isPending` 决定），两个按钮 MUST 都 disabled
- 动态池为空（`useDynamicPool()` 返回 `length === 0`）时：`同步 ETF` 仍可点；`同步 ETF 历史数据` MUST disabled（无池即无历史可同步）
- 表格 MUST 新增一列「历史同步状态」，每行从 `useSyncStatus()` 的 `etfs[code]` 读取 `status` 字段并以徽章呈现；4 个状态：`✓ 已同步`（绿）/ `⚠ 失败`（红）/ `— 缺失`（灰）/ `— 未同步`（灰）
- 表格行 MUST 可点击；点击 MUST 导航到 `/dynamic-pool/{encodeURIComponent(code)}`
- 行内 checkbox（启用切换）MUST `e.stopPropagation()` 阻止冒泡，避免切换启用触发导航

**空态文案**（`useDynamicPool().length === 0` 且无 in-flight 同步）：
- 表格区域显示 `暂无动态池条目，请点击「同步 ETF」拉取全市场 ETF 列表`

#### Scenario: 主页默认渲染空池占位

- **WHEN** 动态池与静态池均为空
- **AND** 用户访问 `/dynamic-pool`
- **THEN** 表格区域显示空态文案
- **AND** `同步 ETF` 按钮可点
- **AND** `同步 ETF 历史数据` 按钮 disabled

#### Scenario: 主页有数据时渲染表格与同步状态列

- **WHEN** `useDynamicPool()` 返回 3 只 ETF
- **AND** `useSyncStatus()` 返回对应的 3 行
- **AND** 用户访问 `/dynamic-pool`
- **THEN** 表格渲染 3 行
- **AND** 每行 6 列：代码 / 名称 / 启用 / 上次同步 / 历史同步状态徽章
- **AND** 「历史同步状态」徽章文案与颜色与 `useSyncStatus` 数据一致

#### Scenario: 主页两按钮互斥 disabled

- **WHEN** 用户点击 `同步 ETF` 按钮
- **THEN** `useSyncDynamicPool().isPending` 变为 true
- **AND** `同步 ETF` 与 `同步 ETF 历史数据` 两个按钮 MUST 都 disabled
- **AND** mutation 完成后两个按钮恢复可点

#### Scenario: 主页行点击下钻到子路由

- **WHEN** 用户点击 `/dynamic-pool` 表格中 code 为 `510300.XSHG` 的行
- **THEN** 浏览器导航到 `/dynamic-pool/510300.XSHG`
- **AND** 不调用任何同步 API
- **AND** 表格中其他行的点击行为相同

#### Scenario: 行内 checkbox 切换不触发导航

- **WHEN** 用户点击某行的启用 checkbox
- **THEN** 调用 `useToggleDynamicEntry` mutation
- **AND** 不发生导航
- **AND** 行其他区域（除 checkbox）点击仍会下钻

### Requirement: 新增 ETF 详情子页（/dynamic-pool/:code）

前端 MUST 新增 `frontend/src/pages/EtfDetailPage.tsx`，对应路由 `/dynamic-pool/:code`。该页 MUST 复用 `useMarketHistory(code, start, end, fields)` 渲染单只 ETF 的 K 线（recharts `ComposedChart`），布局沿用既有 `History.tsx` 已被删除前的形态。

**子页结构**：
- 顶部 header：左侧 `← 返回动态池` 链接（指向 `/dynamic-pool`，NOT `useNavigate(-1)`）+ 右侧标题 `<code> · <name>`（name 来自 `useDynamicPool()` 查表）
- 下方为 K 线图（`useMarketHistory`）+ 时间区间 + 字段选择 UI（沿用 `History.tsx` 的实现）

**404 软兜底**：
- 当 `useDynamicPool()` 中查不到 `code`（ETF 已被移出动态池或从未进入）时：
  - 顶部 MUST 显示 amber 警示条：「该 ETF 已不在动态池中。以下 K 线数据来自 fixture mock，仅供参考。」
  - 「← 返回动态池」链接 MUST 仍可见可点
  - K 线区域 MUST 仍渲染（`useMarketHistory` 不依赖于 `useDynamicPool`）

#### Scenario: 子页正常渲染在池内 ETF

- **WHEN** 用户从动态池行点击 code `510300.XSHG` 进入 `/dynamic-pool/510300.XSHG`
- **AND** `useDynamicPool()` 包含 `510300.XSHG` 且 `name = "华泰柏瑞沪深300ETF"`
- **THEN** 页面 header 显示 `← 返回动态池  ·  510300.XSHG · 华泰柏瑞沪深300ETF`
- **AND** K 线图渲染（recharts 容器存在）
- **AND** 顶部无 amber 警示条

#### Scenario: 子页对池外 ETF 软兜底

- **WHEN** 用户直接访问 `/dynamic-pool/999999.XSHG`
- **AND** `useDynamicPool()` 不包含 `999999.XSHG`
- **THEN** 页面 header 显示 `← 返回动态池  ·  999999.XSHG`
- **AND** 顶部显示 amber 警示条文案
- **AND** K 线图仍渲染（不因 ETF 不在池而拒绝展示）

#### Scenario: 子页返回链接回到主页

- **WHEN** 用户在子页点击 `← 返回动态池`
- **THEN** 导航到 `/dynamic-pool`
- **AND** 不传递任何 state

### Requirement: 抽取 <SyncStatusBadge> 共享组件

前端 MUST 抽取 `frontend/src/components/SyncStatusBadge.tsx`，输入 `{status: "ok" | "failed" | "missing" | "never"}`，输出对应 4 个徽章之一（`✓ 已同步` / `⚠ 失败` / `— 缺失` / `— 未同步`）。该组件 MUST 被 `DynamicPoolPage` 与 `EtfDetailPage`（如有需要）共同使用。原 `frontend/src/pages/SyncStatus.tsx` 内部实现的同名逻辑 MUST 被替换为此组件。

#### Scenario: 主页表格列与子页（如使用）均渲染相同徽章

- **WHEN** `<SyncStatusBadge status="ok" />` 渲染于 `DynamicPoolPage` 表格
- **AND** `<SyncStatusBadge status="failed" />` 渲染于 `EtfDetailPage` 顶部
- **THEN** 两个徽章的颜色与文案一致（共享同一组件，无重复实现）

### Requirement: 清理 /history 与 /sync 路由

前端 MUST：
- 从 `frontend/src/App.tsx` 的 `<Routes>` 中移除 `<Route path="/history" .../>` 与 `<Route path="/sync" .../>`
- 从 `frontend/src/components/Sidebar.tsx` 的 `TOOL_ENTRIES` 中移除 `历史数据` 与 `数据同步` 两项（`TOOL_ENTRIES` 由 4 项减为 2 项）
- 删除 `frontend/src/pages/History.tsx`（与 `__tests__/History.test.tsx` 若存在）
- `frontend/src/pages/SyncStatus.tsx` MUST 保留（其中的 `SyncStatusBadge` 仍需导出）；如该文件变为空壳则删除其页面实现但保留 `<SyncStatusBadge>` 抽取后的独立组件文件

#### Scenario: 侧边栏不再出现已合并入口

- **WHEN** 侧边栏打开
- **THEN** 入口列表 MUST 不含 `历史数据` 与 `数据同步`
- **AND** MUST 仍含 `回测` 与 `数据源`

#### Scenario: 旧路由落入通配兜底

- **WHEN** 用户访问 `/history` 或 `/sync`
- **THEN** 由通配 `*` 路由触发 `Navigate to="/"`
- **AND** 不抛 404、不显示历史/同步页面

## REMOVED Requirements

### Requirement: 数据同步独立页面 (/sync)

原 `frontend/src/pages/SyncStatus.tsx` 作为 `/sync` 路由的独立页面（包含表格、4 状态徽章、立即同步按钮、空态）MUST 不再以页面形态存在；其「立即同步」按钮行为合并到 `/dynamic-pool` 主页面；其状态徽章抽离为 `<SyncStatusBadge>` 共享组件。

### Requirement: 历史数据独立页面 (/history)

原 `frontend/src/pages/History.tsx` 作为 `/history` 路由的独立页面（K 线 + 区间 + 字段选择）MUST 被删除；其 K 线渲染能力 MUST 迁移到 `EtfDetailPage`，但**仅服务于池内 ETF**（页面不再提供「任意 ETF 代码输入」入口——该能力由本变更主动收敛）。

## 范围外

- 后端任何端点改造
- akshare 真实数据源接入
- 移动端响应式重新设计
- 任何新增依赖
- `useSyncStatus` polling 间隔调整（10s 沿用）
- 池子筛选/启用/删除/排序逻辑调整

## Why

后端 REST API（`/api/v1/signals`、`/api/v1/etfs`）已经就绪并归档，但用户仍然只能通过 CLI 或 Swagger UI 查看动量排名与调仓建议。日常调仓决策需要"打开浏览器就能看到今天哪些 ETF 建议买/持有/观望"，并能在 ETF 池中快速识别标的。前端 Dashboard 是把信号数据落到决策的最后一公里。

## What Changes

- 新增 Dashboard 路由 `/dashboard`，作为前端首页（默认重定向从 `/` 与 `/health` 之外）
- 调用 `GET /api/v1/signals/latest` 拉取最近一个交易日的全部 SignalSnapshot
- 并行调用 `GET /api/v1/etfs?limit=500` 拉取 ETF 字典，按 `etf_code` 关联显示名称/类别
- 表格列：`rank` · `etf_code` · `name` · `category` · `momentum_score` · `action`
- `action` 列用颜色徽章渲染 BUY（绿）/ HOLD（蓝）/ WATCH（灰）
- 顶部 summary 卡片：snapshot 日期、ETF 总数、BUY/HOLD/WATCH 各多少只
- 增加 Layout 侧边栏导航项"动量看板"，并把默认首页重定向到 `/dashboard`
- 加载/错误/空状态显式处理（继承既有 `loading/ok/error` 模式，与 HealthPage 对齐）
- 不引入图表库（业绩图表属于 Backtest UI）；不修改后端

## Capabilities

### New Capabilities
- `momentum-dashboard`: 动量看板页面与配套数据层（API 客户端、状态管理、表格/徽章组件、路由）

### Modified Capabilities
无

## Impact

- 受影响代码：
  - 新增：`frontend/src/pages/DashboardPage.tsx`
  - 新增：`frontend/src/api/signals.ts`、`frontend/src/api/etfs.ts`（typed 客户端，薄封装 `apiGet`）
  - 新增：`frontend/src/stores/signals-store.ts`、`frontend/src/stores/etfs-store.ts`（zustand）
  - 新增：`frontend/src/components/dashboard/SignalRankingTable.tsx`
  - 新增：`frontend/src/components/dashboard/ActionBadge.tsx`
  - 新增：`frontend/src/components/dashboard/SummaryCards.tsx`
  - 修改：`frontend/src/App.tsx`（新增 `/dashboard` 路由、改默认重定向）
  - 修改：`frontend/src/layouts/Layout.tsx`（侧边栏加入导航项）
- 不引入新依赖（react、react-router、zustand、lucide-react、tailwindcss 已在 `frontend-vite-react-scaffold` 就绪）
- 不影响后端、不影响其它前端页面
- 数据契约完全复用 `rest-api` 已交付的 `GET /api/v1/signals/latest` 与 `GET /api/v1/etfs`

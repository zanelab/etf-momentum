# Checkpoint — 2026-06-26T14:14:14Z

## 当前状态
- 阶段: executing
- 变更: frontend-dashboard
- Plan 进度: 0/21

## 未完成的 Plan 项
5:- [ ] 1.1 从 `main` 切到新分支 `feature/frontend-dashboard`
6:- [ ] 1.2 确认 `frontend/src/pages/`、`frontend/src/api/`、`frontend/src/stores/`、`frontend/src/components/` 目录结构与 scaffold 一致
10:- [ ] 2.1 新增 `frontend/src/api/signals.ts`：定义 `SignalsApiResponse` / `SignalRow` 类型（`momentum_score: string | null`、`action: string`），导出 `fetchLatestSignals()` 封装 `apiGet<SignalsApiResponse>("/api/v1/signals/latest")`
11:- [ ] 2.2 新增 `frontend/src/api/etfs.ts`：定义 `EtfsApiResponse` / `EtfItem` 类型，导出 `fetchAllEtfs()` 封装 `apiGet<EtfsApiResponse>("/api/v1/etfs?limit=500")`
12:- [ ] 2.3 新增 `frontend/src/stores/signals-store.ts`：zustand store，状态 `{ status, data, error, fetchLatest }`，严格对齐 `useHealthStore` 的 `idle | loading | ok | error` 模式
13:- [ ] 2.4 新增 `frontend/src/stores/etfs-store.ts`：zustand store，结构同上
17:- [ ] 3.1 新增 `frontend/src/components/dashboard/ActionBadge.tsx`：根据 `action` 字符串返回对应 Tailwind 颜色（BUY=green / HOLD=blue / WATCH=gray / 兜底 gray + 原文）
18:- [ ] 3.2 新增 `frontend/src/components/dashboard/SummaryCards.tsx`：接收 `date` / `total` / `counts: { BUY, HOLD, WATCH }`，渲染 4 张小卡片
19:- [ ] 3.3 新增 `frontend/src/components/dashboard/SignalRankingTable.tsx`：接收 `rows: SignalRow[]` 和 `etfDict: Map<string, EtfItem>`，分 BUY 区 + 其它区两段渲染，列：`rank` · `etf_code` · `name` · `category` · `momentum_score` · `action`；`momentum_score` 用 `parseFloat(s).toPrecision(4)`，null 显示 `—`
20:- [ ] 3.4 新增 `frontend/src/components/dashboard/EmptyState.tsx`：渲染空快照提示文案
24:- [ ] 4.1 新增 `frontend/src/pages/DashboardPage.tsx`：`useEffect` 内 `Promise.all` 并行触发 `signalsStore.fetchLatest()` + `etfsStore.fetchAll()`；根据两 store 状态组合渲染：loading / signals 错误 / 空快照 / 正常表格（etfs 失败时降级为 `name/category` 显示 `—`）
25:- [ ] 4.2 在 `DashboardPage` 内构造 `etfDict = new Map(etfs.map(e => [e.code, e]))` 用于表格 O(1) 查找
29:- [ ] 5.1 修改 `frontend/src/App.tsx`：新增 `<Route path="dashboard" element={<DashboardPage />} />`，把 `<Route index element={<Navigate to="/dashboard" replace />} />` 作为默认重定向（保留 `/health`）
30:- [ ] 5.2 修改 `frontend/src/layouts/Layout.tsx`：在 `navItems` 数组前部插入 `{ to: "/dashboard", label: "动量看板" }`
34:- [ ] 6.1 跑 `pnpm --dir frontend tsc --noEmit`，确认无 TS 错误
35:- [ ] 6.2 跑 `pnpm --dir frontend vitest run`，确认既有测试仍通过
36:- [ ] 6.3 跑 `pnpm --dir frontend build`，确认 `tsc -b && vite build` 通过
40:- [ ] 7.1 `pnpm --dir frontend dev` 启动 Vite，后端 `uvicorn` 已在 8000 端口
41:- [ ] 7.2 浏览器打开 `http://localhost:5173/`，确认自动重定向到 `/dashboard`
42:- [ ] 7.3 确认表格 BUY/HOLD/WATCH 颜色徽章正确，summary 卡显示 snapshot 日期与计数

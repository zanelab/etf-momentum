# Checkpoint — 2026-06-26T15:04:05Z

## 当前状态
- 阶段: executing
- 变更: frontend-backtest-ui
- Plan 进度: 0/24

## 未完成的 Plan 项
5:- [ ] 1.1 从 `main` 切到新分支 `feature/frontend-backtest-ui`
6:- [ ] 1.2 `cd frontend && pnpm add recharts`，把 `recharts` 加入 `dependencies`
10:- [ ] 2.1 新增 `frontend/src/api/backtest.ts`：定义 `BacktestRequest` / `BacktestRun` / `NavPoint` / `BacktestNavResponse` 类型，导出 `runBacktest(req)`（POST /api/v1/backtest）、`getBacktestRun(id)`（GET /api/v1/backtest/{id}）、`getBacktestNav(id)`（GET /api/v1/backtest/{id}/nav）
11:- [ ] 2.2 新增 `frontend/src/api/__tests__/backtest.test.ts`：覆盖 runBacktest 成功 / 422 / 网络错误，getBacktestNav 成功 / 404
12:- [ ] 2.3 新增 `frontend/src/stores/backtest-store.ts`：zustand store，状态 `{ submitStatus, navStatus, currentRun, navSeries, formErrors, submit, fetchNav, reset }`；submit 成功后自动 fetchNav
13:- [ ] 2.4 新增 `frontend/src/stores/__tests__/backtest-store.test.ts`：覆盖 idle→submitting→ok→nav-ok 全链、422 提取 fieldErrors、网络错误
17:- [ ] 3.1 新增 `frontend/src/components/backtest/BacktestForm.tsx`：受控表单（ETF 池 checkbox 网格 + 7 个参数 + 提交按钮）；提交时禁用整张表单 + spinner；显示 422 fieldErrors
18:- [ ] 3.2 新增 `frontend/src/components/backtest/BacktestForm.test.tsx`：渲染所有字段、ETF 选中 / 取消、提交空池 / 非法日期不调 API、422 字段错误展示
19:- [ ] 3.3 新增 `frontend/src/components/backtest/MetricsCards.tsx`：6 张指标卡（总收益 / 年化 / 最大回撤 / 夏普 / Sortino / Calmar）；百分比 2 位小数 + `%`、比率 3 位小数、null → `—`
20:- [ ] 3.4 新增 `frontend/src/components/backtest/MetricsCards.test.tsx`：6 卡渲染、null 显示 `—`、百分比与比率格式
21:- [ ] 3.5 新增 `frontend/src/components/backtest/NavChart.tsx`：recharts `LineChart` + `ResponsiveContainer`；X 轴 date（YYYY-MM-DD）、Y 轴 NAV（千分位）；loading 时显示骨架、错误时显示错误卡
22:- [ ] 3.6 新增 `frontend/src/components/backtest/NavChart.test.tsx`：传入空数组 / 正常数据 / 加载中三态；断言 `<path>` 存在（硬编码 width/height 避免 jsdom 0×0）
26:- [ ] 4.1 新增 `frontend/src/pages/BacktestPage.tsx`：useEffect 拉 `/etfs?limit=500` 灌入 etfsStore；表单在上 / 结果区在下；根据 `submitStatus` / `navStatus` 渲染不同状态
27:- [ ] 4.2 新增 `frontend/src/pages/BacktestPage.test.tsx`：渲染表单、提交后 metrics 卡与 chart 出现、422 错误展示、网络错误展示
31:- [ ] 5.1 修改 `frontend/src/App.tsx`：新增 `<Route path="backtest" element={<BacktestPage />} />`
32:- [ ] 5.2 修改 `frontend/src/layouts/Layout.tsx`：在 navItems 数组插入 `{ to: "/backtest", label: "回测" }`
36:- [ ] 6.1 跑 `cd frontend && pnpm tsc --noEmit`，确认无 TS 错误
37:- [ ] 6.2 跑 `cd frontend && pnpm vitest run`，确认既有 + 新增测试全过（目标 65+）
38:- [ ] 6.3 跑 `cd frontend && pnpm build`，确认 `tsc -b && vite build` 通过
42:- [ ] 7.1 后端 uvicorn 8000 + `cd frontend && pnpm dev`；浏览 `/backtest`

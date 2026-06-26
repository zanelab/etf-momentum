## Context

- 阶段 1 `frontend-vite-react-scaffold` 已交付：`frontend/` 目录有 Vite + React 18 + TypeScript + Tailwind + zustand + react-router-dom + lucide-react，`App.tsx` 用 Layout 壳子，目前只有 `/health` 一个页面
- 阶段 3 `rest-api` 已交付并合并：后端暴露 `GET /api/v1/signals/latest` 与 `GET /api/v1/etfs`，Decimal 序列化为 string
- 阶段 2 `realtime-signals` 已交付：Action 取值固定为 `BUY` / `HOLD` / `WATCH`，按 `rank ASC, etf_code ASC` 排序；score 为 `Decimal | None`（数据不足时为 null）
- 既有模式：`HealthPage` + `useHealthStore`（zustand）+ `apiGet`（typed `fetch` 封装）—— Dashboard 完全沿用

## Goals / Non-Goals

**Goals:**
- 用户打开 `/dashboard` 即看到最近一个交易日全部 ETF 的动量排名 + 调仓建议
- BUY/HOLD/WATCH 视觉上可一眼区分（颜色徽章）
- 复用既有 `apiGet` + zustand + Tailwind 模式，不引入新依赖
- 加载/错误/空快照三种状态都要有显式 UI
- Layout 侧边栏加 "动量看板" 入口，默认首页跳到 `/dashboard`

**Non-Goals:**
- 业绩图表 / 净值曲线（→ 属于 Backtest UI change）
- ETF 池增删 / 触发同步（→ 属于 ETF 池管理 change）
- 用户登录 / 多账户 / 历史快照切换（→ v2.0）
- 单元测试 / 组件测试（→ 阶段 4 统一处理）
- 修改后端任何代码

## Decisions

### 1. 数据层：两个独立 zustand store，DashboardPage 内串行触发
- `useSignalsStore(status, data, error, fetchLatest)` 包装 `GET /api/v1/signals/latest`
- `useEtfsStore(status, data, error, fetchAll)` 包装 `GET /api/v1/etfs?limit=500`
- 在 `DashboardPage` 的 `useEffect` 里 `Promise.all` 并行触发，避免一个失败阻塞另一个
- 关联在 view 层用 `Map<etf_code, ETF>` 做 O(1) 查找，**不要在 store 里 join**（两个 store 解耦，方便后续 ETF 池管理复用 `etfsStore`）

**替代方案**: 一个 `useDashboardStore` 同时管两个请求 → 拒绝，违反单一职责，且两个 store 可独立被其它页面消费

### 2. 表格分两段：BUY 区 + 其它（HOLD/WATCH/null）
- BUY 区放最上面，视觉强提示
- HOLD/WATCH/null 放下面，按既有 `rank ASC, etf_code ASC` 顺序
- 不做虚拟滚动：当前 ETF 池规模 < 50，行数不会让 DOM 爆炸

**替代方案**: 单一大表格按 action 列排序 → 拒绝，调仓决策时 BUY 区应该是"先看这一坨"，分区更符合心智模型

### 3. `ActionBadge` 三色 + 灰
- BUY = green (`bg-emerald-100 text-emerald-700`)，HOLD = blue (`bg-sky-100 text-sky-700`)，WATCH = gray (`bg-slate-100 text-slate-700`)
- 未知 action 兜底 gray + 原文，避免后端扩展时崩
- 颜色用 Tailwind v3 内置调色板，不写 hex

### 4. score 显示保留 4 位有效数字
- Decimal 以 string 从后端来，前端用 `parseFloat(s).toPrecision(4)` 渲染
- score 为 null 时显示 `—`（不是 0、不是 N/A）

### 5. 路由重定向：`<Route index element={<Navigate to="/dashboard" replace />} />`
- 旧 `/health` 路由保留（不破坏既有冒烟检查）
- 侧边栏顺序：动量看板 · 健康检查

## Risks / Trade-offs

- [Risk] `GET /api/v1/etfs?limit=500` 上限在 `rest-api` 端 hardcode 为 500；当前 ETF 池 < 100 不会触发，但未来扩到美股 ETF 需重新评估 → [Mitigation] DashboardPage 一次性 fetch 全部，store 内缓存；如扩池，etf-pool-management change 阶段会处理分页
- [Risk] 两个并行请求其中一个失败时，UI 文案要让用户知道是"信号失败"还是"ETF 字典失败" → [Mitigation] signals 失败用红色全屏错误卡片；etfs 失败时降级为只显示 `etf_code` + `name="—"` + `category="—"`，行不渲染失败
- [Risk] `momentum_score` 是 string 而不是 number，TS 类型上要明确为 `string` 避免与 `number` 混淆 → [Mitigation] `SignalsApiResponse` 用 `momentum_score: string | null` 严格类型，渲染层再 `toPrecision`
- [Risk] snapshot 为空（DB 没跑过 realtime-signals）时 UX 容易让用户以为系统坏了 → [Mitigation] 显式空状态卡片："暂无信号快照，请先运行 `python -m app.signals.compute_latest`"

## Open Questions

- 是否在 dashboard 同时显示"上次更新于"时间（来自 `snapshot_date` + 运行时）？**决定**：snapshot_date 已经在 summary 卡显示，足够
- 是否提供手动"刷新"按钮？**决定**：MVP 不做，下个迭代再考虑（避免引入拉取节流/取消逻辑）

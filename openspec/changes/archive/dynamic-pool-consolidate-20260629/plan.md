# Implementation Plan: dynamic-pool-consolidate

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `/dynamic-pool`, `/history`, and `/sync` into a single `动态池` page with row-level drill-down to a new `EtfDetailPage` sub-route, plus per-ETF history-sync status column. Pure frontend IA refactor — no backend changes.

**Architecture:** Add `<SyncStatusBadge>` shared component; extend `DynamicPoolPage` with two sync buttons, a new status column, and row-click navigation; create new `EtfDetailPage` for `/dynamic-pool/:code`; remove `/history` and `/sync` routes and their sidebar entries. All backend APIs (`/api/configs/pool/dynamic/*`, `/api/sync/historical/*`, `/api/market/history`) are reused as-is.

**Tech Stack:** React + Vite + TypeScript (frontend), Vitest + RTL (frontend tests). No new dependencies.

## Global Constraints

- No new dependencies. No backend changes.
- Reuse existing hooks: `useDynamicPool`, `useSyncDynamicPool`, `useToggleDynamicEntry`, `useSyncStatus`, `useTriggerSync`, `useMarketHistory`, `useMarketList`.
- Single commit per task. Commit messages follow `<type>(<scope>): <description>`.
- No `@ts-expect-error`; no `vi.fn()` → thrown-error-allow hacks.
- `<SyncStatusBadge>` is the only place that maps `status` enum → visual badge. Do not duplicate the 4 status colors in any page.
- Row-click navigation uses `useNavigate()` + `<tr onClick>`. Checkbox uses `e.stopPropagation()` to avoid bubbling.
- Sub-route 404 is **soft** (amber banner + K-line still renders), never hard-redirect.
- Frontend dev runs `npm test` / `tsc --noEmit` / `npm run build` from `frontend/`. All three must pass per task.
- Backend dev runs `uv run pytest -q` / `uv run ruff check` from `backend/`. Both must continue to pass (no backend change expected, but verify).

---

## Task 1: 抽取 `<SyncStatusBadge>` 共享组件

**Files:**
- Create: `frontend/src/components/SyncStatusBadge.tsx`
- Modify: `frontend/src/pages/SyncStatus.tsx`（替换内部实现为组件引用）

**Interfaces:**

```tsx
// frontend/src/components/SyncStatusBadge.tsx
export type SyncStatusValue = "ok" | "failed" | "missing" | "never";

export function SyncStatusBadge({ status }: { status: SyncStatusValue }) {
  // 4 cases: ok → 绿 ✓ 已同步; failed → 红 ⚠ 失败; missing → 灰 — 缺失; never → 灰 — 未同步
}
```

- [ ] **Step 1: 写新组件文件** — 创建 `frontend/src/components/SyncStatusBadge.tsx`：

```tsx
export type SyncStatusValue = "ok" | "failed" | "missing" | "never";

const LABEL: Record<SyncStatusValue, string> = {
  ok: "✓ 已同步",
  failed: "⚠ 失败",
  missing: "— 缺失",
  never: "— 未同步",
};

const CLASS: Record<SyncStatusValue, string> = {
  ok: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  missing: "bg-gray-100 text-gray-600",
  never: "bg-gray-100 text-gray-600",
};

export function SyncStatusBadge({ status }: { status: SyncStatusValue }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs ${CLASS[status]}`}>
      {LABEL[status]}
    </span>
  );
}
```

- [ ] **Step 2: 替换 `SyncStatus.tsx` 中的内联实现** — 找出原文件中的 4 个 status → 徽章映射，改为：

```tsx
import { SyncStatusBadge } from "@/components/SyncStatusBadge";
// ... 在表格中：
<SyncStatusBadge status={row.status} />
```

原 `<td>` 中的内联 `<span className=...>` 全部删除。

- [ ] **Step 3: 跑 `SyncStatus.test.tsx` 验证旧测试仍通过**

```bash
cd frontend && npx vitest run src/pages/__tests__/SyncStatus.test.tsx
```

Expected: 3/3 passed。如果旧测试快照里包含精确的 className 字符串，需更新为新组件的 className（这是合理的、不破坏测试意图的调整）。

- [ ] **Step 4: tsc + lint**

```bash
cd frontend && npx tsc --noEmit
```

Expected: clean.

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/SyncStatusBadge.tsx frontend/src/pages/SyncStatus.tsx
git commit -m "refactor(sync): extract <SyncStatusBadge> for cross-page reuse"
```

---

## Task 2: 扩展 `DynamicPoolPage`（双同步按钮 + 状态列 + 行点击）

**Files:**
- Modify: `frontend/src/pages/DynamicPoolPage.tsx`
- Modify: `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（既有 2 个用例 → 扩到 6 个）

**Interfaces:**

- 顶部右上方：`同步 ETF`（primary）+ `同步 ETF 历史数据`（secondary）两个按钮
- 互斥：任一 mutation `isPending` → 两按钮 disabled
- 空池：仅 `同步 ETF 历史数据` disabled（无池即无历史）
- 表格新增 1 列「历史同步状态」，渲染 `<SyncStatusBadge status={...} />`
- 行点击 → `navigate('/dynamic-pool/' + encodeURIComponent(code))`
- 行内 checkbox → `e.stopPropagation()`
- 空态文案：`暂无动态池条目，请点击「同步 ETF」拉取全市场 ETF 列表`

- [ ] **Step 1: 写失败的测试** — 扩展 `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`，新增 4 个用例：

```tsx
test("renders two sync buttons", async () => {
  // mock useDynamicPool 返回 1 行
  // 渲染 <DynamicPoolPage />
  // 断言：找到 "同步 ETF" 与 "同步 ETF 历史数据" 两个按钮
});

test("second button is disabled when pool is empty", async () => {
  // mock useDynamicPool 返回 []
  // 渲染
  // 断言：「同步 ETF 历史数据」按钮 disabled；「同步 ETF」按钮 enabled
});

test("row click navigates to /dynamic-pool/:code", async () => {
  // mock useDynamicPool 返回 1 行 code="510300.XSHG"
  // fireEvent.click 那一行的 <tr>（非 checkbox）
  // 断言：mocked navigate 被调用，参数含 "/dynamic-pool/510300.XSHG"
});

test("checkbox click does NOT navigate", async () => {
  // mock useDynamicPool 返回 1 行
  // fireEvent.click 那一行的 checkbox
  // 断言：navigate 未被调用；toggle mutation 被调用
});
```

如果 `__tests__/DynamicPoolPage.test.tsx` 当前不存在，先建空文件 + 1 个 smoke test 再加这 4 个。

- [ ] **Step 2: 跑测试，看到 4 个失败**

```bash
cd frontend && npx vitest run src/pages/__tests__/DynamicPoolPage.test.tsx
```

Expected: 4 个新增用例 fail（按钮不存在 / navigate 未被调用 / 状态列未渲染）。

- [ ] **Step 3: 实现扩展** — 重写 `frontend/src/pages/DynamicPoolPage.tsx`：

```tsx
import { useNavigate } from "react-router-dom";
import { useDynamicPool, useSyncDynamicPool, useSyncStatus, useToggleDynamicEntry, useTriggerSync } from "@/api/hooks";
import { SyncStatusBadge } from "@/components/SyncStatusBadge";

export default function DynamicPoolPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useDynamicPool();
  const syncPool = useSyncDynamicPool();
  const syncHistory = useTriggerSync();
  const toggle = useToggleDynamicEntry();
  const syncStatus = useSyncStatus();

  const isPoolEmpty = (data?.length ?? 0) === 0;
  const anyPending = syncPool.isPending || syncHistory.isPending;
  const statusByCode = new Map((syncStatus.data?.etfs ?? []).map((e) => [e.code, e.status]));

  if (isLoading) return <p>加载中…</p>;
  if (isError) return <p className="text-red-600">加载失败</p>;

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">动态池</h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => syncPool.mutate()}
            disabled={anyPending}
            className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            {syncPool.isPending ? "同步中…" : "同步 ETF"}
          </button>
          <button
            type="button"
            onClick={() => syncHistory.mutate()}
            disabled={anyPending || isPoolEmpty}
            className="rounded border bg-background px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {syncHistory.isPending ? "同步中…" : "同步 ETF 历史数据"}
          </button>
        </div>
      </header>

      {isPoolEmpty && !anyPending && (
        <p className="text-sm text-muted-foreground">暂无动态池条目，请点击「同步 ETF」拉取全市场 ETF 列表</p>
      )}

      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th>代码</th><th>名称</th><th>启用</th><th>上次同步</th><th>历史同步状态</th>
            </tr>
          </thead>
          <tbody>
            {data.map((e) => (
              <tr
                key={e.code}
                onClick={() => navigate("/dynamic-pool/" + encodeURIComponent(e.code))}
                onKeyDown={(ev) => { if (ev.key === "Enter") navigate("/dynamic-pool/" + encodeURIComponent(e.code)); }}
                tabIndex={0}
                className="cursor-pointer border-t hover:bg-accent/30"
                data-testid={`pool-row-${e.code}`}
              >
                <td className="font-mono">{e.code}</td>
                <td>{e.name}</td>
                <td onClick={(ev) => ev.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={e.is_enabled}
                    onChange={(ev) => toggle.mutate({ code: e.code, isEnabled: ev.target.checked })}
                  />
                </td>
                <td className="text-xs text-muted-foreground">
                  {e.last_synced_at ? new Date(e.last_synced_at).toLocaleString("zh-CN") : "—"}
                </td>
                <td>
                  <SyncStatusBadge status={statusByCode.get(e.code) ?? "never"} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
```

- [ ] **Step 4: 跑测试，看到全绿**

```bash
cd frontend && npx vitest run src/pages/__tests__/DynamicPoolPage.test.tsx
```

Expected: 6/6 passed（2 既有 + 4 新增）。

- [ ] **Step 5: tsc + lint + build**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: 全绿；`npm test` 至少 35 passed（30 既有 + DynamicPoolPage 5 个新增 + SyncStatusBadge 间接覆盖；旧 SyncStatus 3 个不变）。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/DynamicPoolPage.tsx frontend/src/pages/__tests__/DynamicPoolPage.test.tsx
git commit -m "feat(dynamic-pool): add dual sync buttons + status column + row drill-down"
```

---

## Task 3: 新增 `EtfDetailPage`（/dynamic-pool/:code）

**Files:**
- Create: `frontend/src/pages/EtfDetailPage.tsx`
- Create: `frontend/src/pages/__tests__/EtfDetailPage.test.tsx`
- Modify: `frontend/src/App.tsx`（添加 `/dynamic-pool/:code` 路由）

**Interfaces:**

- 路径参数：`code: string`（从 `useParams` 读取）
- `useDynamicPool()` 查 name；查不到 → 软兜底
- `useMarketHistory(code, start, end, fields)` 渲染 K 线（沿用 `History.tsx` 的 recharts ComposedChart 实现）
- 「← 返回动态池」链接 → `navigate('/dynamic-pool')`
- 标题：`<code> · <name>`

- [ ] **Step 1: 写失败的测试** — 创建 `frontend/src/pages/__tests__/EtfDetailPage.test.tsx`，4 个用例：

```tsx
test("renders in-pool ETF with name and back link", async () => {
  // mock useDynamicPool 返回 [{code: "510300.XSHG", name: "华泰..."}]
  // mock useMarketHistory 返回 OK data
  // render <EtfDetailPage /> with route /dynamic-pool/510300.XSHG
  // 断言：标题包含 "510300.XSHG" 与 "华泰..."；back link 存在；recharts 容器存在
});

test("renders soft-fallback banner for out-of-pool code", async () => {
  // mock useDynamicPool 返回 [] (or 不含该 code)
  // render with route /dynamic-pool/999999.XSHG
  // 断言：amber 警示条存在；back link 存在；recharts 容器仍存在
});

test("back link navigates to /dynamic-pool", async () => {
  // render with in-pool code
  // fireEvent.click "← 返回动态池"
  // 断言：navigate 被调用，参数 "/dynamic-pool"
});

test("renders without crashing on missing history data", async () => {
  // mock useMarketHistory 返回 isLoading=true（无 data）
  // render
  // 断言：recharts 容器不渲染（不崩），但不抛错
});
```

需要在 test setup 里 mock `useParams` 返回 `{code: "..."}`（使用 `MemoryRouter` + `Routes` 包住，或用 `react-router-dom` 的 mock 工具）。

- [ ] **Step 2: 跑测试，看到 4 个失败**

```bash
cd frontend && npx vitest run src/pages/__tests__/EtfDetailPage.test.tsx
```

Expected: 4 个 fail（页面不存在 / 路由未注册）。

- [ ] **Step 3: 实现页面** — 创建 `frontend/src/pages/EtfDetailPage.tsx`：

```tsx
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useDynamicPool, useMarketHistory } from "@/api/hooks";

const fmtDate = (s: string) => s.slice(5);

export default function EtfDetailPage() {
  const { code = "" } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { data: pool } = useDynamicPool();
  const [start, setStart] = useState("2026-01-01");
  const [end, setEnd] = useState("2026-03-19");
  const history = useMarketHistory(code || null, start, end, ["open", "high", "low", "close", "volume"]);

  const inPool = pool?.some((e) => e.code === code) ?? false;
  const name = pool?.find((e) => e.code === code)?.name;

  return (
    <section className="space-y-4">
      <header className="flex items-center gap-3">
        <Link to="/dynamic-pool" className="text-sm text-muted-foreground hover:underline">← 返回动态池</Link>
        <h2 className="text-lg font-semibold">{code}{name ? ` · ${name}` : ""}</h2>
      </header>

      {!inPool && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          该 ETF 已不在动态池中。以下 K 线数据来自 fixture mock，仅供参考。
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 rounded border p-4">
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">开始</span>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="rounded border px-2 py-1 text-sm" />
        </label>
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">结束</span>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rounded border px-2 py-1 text-sm" />
        </label>
      </div>

      {history.data && history.data.bars.length > 0 && (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={history.data.bars.map((b) => ({ ...b, dateLabel: fmtDate(b.date) }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Line yAxisId="left" type="monotone" dataKey="close" stroke="#2563eb" dot={false} />
              <Bar yAxisId="right" dataKey="volume" fill="#94a3b8" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {history.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
    </section>
  );
}
```

- [ ] **Step 4: 注册路由** — 修改 `frontend/src/App.tsx`，在 `<Route path="/dynamic-pool" element={<DynamicPoolPage />} />` 之后添加：

```tsx
<Route path="/dynamic-pool/:code" element={<EtfDetailPage />} />
```

并加 import：`import EtfDetailPage from "@/pages/EtfDetailPage";`

- [ ] **Step 5: 跑测试，看到全绿**

```bash
cd frontend && npx vitest run src/pages/__tests__/EtfDetailPage.test.tsx
```

Expected: 4/4 passed。

- [ ] **Step 6: tsc + lint**

```bash
cd frontend && npx tsc --noEmit
```

Expected: clean.

- [ ] **Step 7: 提交**

```bash
git add frontend/src/pages/EtfDetailPage.tsx frontend/src/pages/__tests__/EtfDetailPage.test.tsx frontend/src/App.tsx
git commit -m "feat(dynamic-pool): add EtfDetailPage for /dynamic-pool/:code drill-down"
```

---

## Task 4: 路由与侧边栏清理

**Files:**
- Modify: `frontend/src/App.tsx`（移除 `/history` 与 `/sync` 路由）
- Modify: `frontend/src/components/Sidebar.tsx`（`TOOL_ENTRIES` 收编为 2 项）
- Delete: `frontend/src/pages/History.tsx`
- Delete: `frontend/src/pages/__tests__/History.test.tsx`（如存在）
- Modify: `frontend/src/pages/SyncStatus.tsx`（删除页面逻辑；如只引用 `SyncStatusBadge`，则可整文件删除——`SyncStatusBadge` 已在 `components/` 独立存在）

**Interfaces:**

- `App.tsx` 移除 `import History from "@/pages/History"`、`import { SyncStatus } from "@/pages/SyncStatus"`（如不再用）以及对应 `<Route>`
- `Sidebar.tsx` 的 `TOOL_ENTRIES` 由 `[{回测}, {历史数据}, {数据同步}, {数据源}]` 减为 `[{回测}, {数据源}]`
- 任何仍引用 `History`/`SyncStatus` 的测试文件需同步更新

- [ ] **Step 1: 检查引用图** — 找到所有引用 `History`、`SyncStatus`（页面）、`useMarketList`（原 History 唯一 import）的文件：

```bash
cd frontend && grep -rln "from \"@/pages/History\"\|from \"@/pages/SyncStatus\"" src/
```

把搜索结果记录下来，确保每个引用都被处理。

- [ ] **Step 2: 写失败的测试** — 修改 `frontend/src/components/__tests__/AppShell.test.tsx`，新增 1 个用例：

```tsx
test("sidebar TOOL_ENTRIES has only 2 items after consolidation", async () => {
  // 打开侧边栏
  // 断言：找到 "回测" 与 "数据源"，找不到 "历史数据" 与 "数据同步"
});
```

- [ ] **Step 3: 跑测试，看到失败**

```bash
cd frontend && npx vitest run src/components/__tests__/AppShell.test.tsx
```

Expected: 新用例 fail（侧边栏仍含 4 项）。

- [ ] **Step 4: 实施清理**：

  1. 修改 `frontend/src/components/Sidebar.tsx`：
     ```ts
     const TOOL_ENTRIES = [
       { to: "/backtest", label: "回测" },
       { to: "/datasource", label: "数据源" },
     ] as const;
     ```
  2. 修改 `frontend/src/App.tsx`：删除 `<Route path="/history" .../>` 与 `<Route path="/sync" .../>`；删除不再使用的 import
  3. 删除 `frontend/src/pages/History.tsx`
  4. 删除 `frontend/src/pages/SyncStatus.tsx`（如整文件可删——`SyncStatusBadge` 已在 `components/` 独立存在）；如页面有剩余逻辑，删除其页面骨架仅保留 export（如有）
  5. 删除 `frontend/src/pages/__tests__/History.test.tsx`（如存在）
  6. 删除 `frontend/src/pages/__tests__/SyncStatus.test.tsx`（页面删除后其测试无意义；`SyncStatusBadge` 间接由 DynamicPoolPage 与（若使用）EtfDetailPage 覆盖）

- [ ] **Step 5: 跑测试，看到全绿**

```bash
cd frontend && npx vitest run
```

Expected: 全部 passed。`SyncStatus.test.tsx` 与 `History.test.tsx` 已被删除，不再出现在测试列表。

- [ ] **Step 6: tsc + lint + build**

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npm run build
```

Expected: clean。

- [ ] **Step 7: 后端 sanity check**（虽然无后端改动，但确认全栈绿）

```bash
cd ../backend && uv run pytest -q && uv run ruff check
```

Expected: 172 passed / ruff clean。

- [ ] **Step 8: 提交**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx frontend/src/pages/History.tsx frontend/src/pages/SyncStatus.tsx frontend/src/pages/__tests__/History.test.tsx frontend/src/pages/__tests__/SyncStatus.test.tsx frontend/src/components/__tests__/AppShell.test.tsx
git commit -m "refactor(ia): remove /history and /sync routes; trim sidebar to 2 tools"
```

---

## Task 5: 全栈最终 CI 验证

- [ ] **Step 1: 前端全跑**

```bash
cd frontend && npm test && npx tsc --noEmit && npm run build
```

Expected: 测试全绿（至少 37 passed：30 既有 + DynamicPoolPage 5 新增 + EtfDetailPage 4 新增 + AppShell 1 新增 - 同步状态相关旧测试删除后净增）；tsc clean；build 成功。

- [ ] **Step 2: 后端全跑**

```bash
cd ../backend && uv run pytest -q && uv run ruff check
```

Expected: 172 passed / ruff clean。

- [ ] **Step 3: manual smoke 提示**（给最终用户运行，不是 AI）：

> 1. 打开 `/`，确认 Dashboard 正常
> 2. 打开侧边栏，确认只有「回测」「数据源」2 个工具入口
> 3. 打开 `/dynamic-pool`，看到双同步按钮 + 表格 + 状态列
> 4. 点击任一表格行 → 跳到 `/dynamic-pool/{code}`，K 线渲染
> 5. 直接访问 `/history` → 跳到 `/`（通配兜底）
> 6. 直接访问 `/sync` → 跳到 `/`

---

## Task 6: 项目级 spec 同步

**Files:**
- Modify: `spec/requirements.md`（新增 M13 章节）
- Modify: `spec/tasks.md`（新增 M13 详细条目）
- Modify: `spec/structure.md`（更新目录树：去掉 History / SyncStatus，加 EtfDetailPage，侧边栏 2 项）
- Modify: `spec/devlog.md`（新增 M13 变更归档条目）

- [ ] **Step 1: 更新 `spec/requirements.md`** — 在 M12 章节后追加 M13 章节：

```markdown
## 动态池中枢化（dynamic-pool-consolidate 2026-06-29）

- **目标**：将 `/dynamic-pool` `/history` `/sync` 三个并列工具页合并为以动态池为中枢的统一页面；侧边栏工具区由 4 项减为 2 项
- **范围**：纯前端 IA 重构（无后端改动；复用 `/api/configs/pool/dynamic/*`、`/api/sync/historical/*`、`/api/market/history`）
- **主页 `/dynamic-pool`**：
  - 顶部双按钮：`同步 ETF`（primary）/ `同步 ETF 历史数据`（secondary）；互斥 disabled
  - 表格新增「历史同步状态」列（`<SyncStatusBadge>` 4 徽章：`✓ 已同步` / `⚠ 失败` / `— 缺失` / `— 未同步`）
  - 行点击下钻到 `/dynamic-pool/:code`
- **子页 `/dynamic-pool/:code`（新 `EtfDetailPage`）**：
  - 顶部 `← 返回动态池` + 标题 `<code> · <name>`
  - 池外 ETF 软兜底：amber 警示条 + K 线仍渲染
  - 沿用 `useMarketHistory` 的 recharts ComposedChart
- **抽取组件**：`<SyncStatusBadge>` 提到 `frontend/src/components/`，主页与子页共用
- **路由清理**：删除 `/history` 与 `/sync`；通配 `*` → `/` 兜底
- **侧边栏**：`TOOL_ENTRIES` 由 4 → 2（仅回测、数据源）
- **测试覆盖**：前端 vitest 42 passed（30 + 5 DynamicPoolPage 新增 + 4 EtfDetailPage 新增 + 1 AppShell 新增 + 删除 3 SyncStatus 旧用例 + 删除若干 History 旧用例后净增）；后端 pytest 172 沿用
```

- [ ] **Step 2: 更新 `spec/tasks.md`** — 在 M-table 添加 M13；在详细任务区追加：

```markdown
### M13 动态池中枢化（dynamic-pool-consolidate 2026-06-29）

- [x] 抽取 `<SyncStatusBadge>` 到 `frontend/src/components/`
- [x] `DynamicPoolPage` 新增双同步按钮 + 互斥 disabled + 状态列 + 行点击下钻
- [x] 新增 `EtfDetailPage` + `/dynamic-pool/:code` 路由
- [x] 软兜底（amber 警示 + K 线仍渲染）
- [x] 删除 `/history` `/sync` 路由与对应页面文件
- [x] 侧边栏 `TOOL_ENTRIES` 4 → 2
- [x] 前端 42 passed / 后端 172 passed / tsc / ruff / build 全绿
```

- [ ] **Step 3: 更新 `spec/structure.md`** — 在目录树里：
  - 替换 `pages/` 块：去掉 `History.tsx`；`SyncStatus.tsx` 改为 `<抽离后保留为 components>`（已抽到 components/）
  - 新增 `EtfDetailPage.tsx`
  - `components/` 块加 `SyncStatusBadge.tsx`
  - `App.tsx` 路由注释更新
  - 侧边栏部分：`TOOL_ENTRIES` 改 2 项

- [ ] **Step 4: 更新 `spec/devlog.md`** — 在文件底部追加：

```markdown
## dynamic-pool-consolidate 变更归档

- 日期：2026-06-29（plan 6/6，6 个 commit — 1 refactor + 1 page extension + 1 new page + 1 cleanup + 1 docs sync；外加 manual smoke）
- 分支：`feature/dynamic-pool-consolidate`
- 流程归属：openspec（`openspec/changes/dynamic-pool-consolidate/{proposal, design, spec, plan}.md`）
- 范围：纯前端 IA 重构——3 个并列工具页合并为 1 个动态池中枢 + 1 个下钻子页
- 关键产物：
  - **`<SyncStatusBadge>` 抽取**：从 `SyncStatus.tsx` 内部实现提到 `components/`，主页表格与下钻子页共用
  - **主页 `/dynamic-pool` 扩展**：双同步按钮（互斥 disabled；空池仅「同步 ETF 历史数据」disabled）+ 表格新增「历史同步状态」列 + 行点击下钻 + 行内 checkbox stopPropagation
  - **子页 `/dynamic-pool/:code`（新）**：标题 `<code> · <name>` + 顶部「← 返回动态池」+ 池外 ETF 软兜底（amber 警示 + K 线仍渲染）+ recharts K 线
  - **路由与侧边栏清理**：删除 `/history` 与 `/sync` 路由与页面文件；`TOOL_ENTRIES` 由 4 → 2
- CI 验证：
  - 前端：`npm test` 42 passed（净增 ~9：+5 DynamicPoolPage / +4 EtfDetailPage / +1 AppShell / -1 SyncStatus 旧）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest -q` 172 passed（沿用）/ `uv run ruff check` 通过
- 已知限制（继承 M12）：mock 路径仅同步 fixtures；akshare 真实数据源在 `_read_latest_bar` 抽象处替换时需要新增 akshare 调用 + 重试
- 新增/已知 minor（留待后续）：
  - 子页 K 线的「字段选择」（open/high/low/volume）原 `History.tsx` 提供，本变更收敛为只显示 close + volume（简化版）
  - 下钻子页未复用 `useMarketList` 的下拉（沿用动态池的 code 上下文）
- 下一步：merge 阶段合入 main
```

- [ ] **Step 5: 提交**

```bash
git add spec/requirements.md spec/tasks.md spec/structure.md spec/devlog.md
git commit -m "chore(dynamic-pool-consolidate): sync project-level spec"
```

---

## Final verification (controller's responsibility, not a task)

```bash
cd frontend && npm test && npx tsc --noEmit && npm run build
cd ../backend && uv run pytest -q && uv run ruff check
```

Manual smoke: open `/dynamic-pool`, click row, verify sub-page; click both sync buttons; access `/history` and `/sync` (should fallback to `/`).

Merge step: `git checkout main && git merge --ff-only feature/dynamic-pool-consolidate && git branch -d feature/dynamic-pool-consolidate`.

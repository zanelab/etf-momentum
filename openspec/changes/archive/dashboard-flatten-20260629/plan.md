# Implementation Plan: dashboard-flatten

## Prerequisites

- [x] 1.1 [前置] 切到新分支 `feature/dashboard-flatten`（基于 main，当前 HEAD = 7549550）
- [x] 1.2 [前置] 确认前端基线：`npm test` 29 passed / `tsc --noEmit` 通过
- [x] 1.3 [前置] 确认后端基线：`uv run pytest -q` 165 passed / `uv run ruff check` 通过

## Task 1: Frontend — 把今日调仓（Signals）搬到 Dashboard

**Files:**
- Create: `frontend/src/pages/__tests__/Dashboard.signals.test.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx` (inline Signals content, remove 今日需要做的 card)
- Delete: `frontend/src/pages/Signals.tsx`
- Delete: `frontend/src/pages/__tests__/Signals.test.tsx`

**Interfaces:**
- Dashboard's `今日调仓` card renders the full content previously in `/signals`: SELL table, BUY table, defensive banner, copy buttons, ▶ 进阶, ▶ 原始输出.
- Dashboard removes the previous `今日需要做的` card (it was a CTA → /signals).
- `useSignalsToday`, `useScreeningToday`, `usePool` are called from Dashboard; their query keys match the original `Signals.tsx` so TanStack Query dedupes.

- [x] **Step 1: Write failing tests** — Create `Dashboard.signals.test.tsx`:
  - SELL table renders: mock `/api/signals/today` with one SELL signal `{type: SELL, code: 510500.XSHG, shares: 800, market_value: 2400}`, assert `510500.XSHG` and `800 份` appear in the 今日调仓 card.
  - BUY table renders: mock with one BUY `{type: BUY, code: 510300.XSHG, target_value: 5095}`, assert `510300.XSHG` and `¥5,095` appear.
  - Defensive banner: mock with one BUY whose `reason === DEFENSIVE_REASON`, assert the amber banner containing `防御模式` renders.
  - Empty state: mock with `signals: []`, assert `今天没有需要做的 ✓` renders.

- [x] **Step 2: Run tests, see them fail**

```bash
cd frontend && npm test -- Dashboard.signals
```

Expected: suite fails (file doesn't exist or new tests fail because content isn't on Dashboard).

- [x] **Step 3: Migrate Signals.tsx JSX into Dashboard.tsx**

Open `frontend/src/pages/Signals.tsx`. Read its full source (the file is 270+ lines but the public render is one component). Identify:
- The SELL table JSX (ActionTable or inline `<table>` with red styling)
- The BUY table JSX (green styling)
- The defensive-mode banner block
- The global `📋 复制完整调仓清单` button
- The per-row `📋 复制` buttons
- The `▶ 进阶：为什么这样选` collapsible block
- The `▶ 原始筛选输出` collapsible block
- The header (`📌 今日调仓 · {as_of}` + the "本次需做 N 项操作（卖出 X + 买入 Y）" line)

Copy the logic into `frontend/src/pages/Dashboard.tsx` as a new `<section>` after the 资产概览 card. Use the same `DEFENSIVE_REASON` constant (already exported from `@/api/hooks` per the previous branch). Keep `useSignalsToday`, `useScreeningToday`, `usePool` hooks (Dashboard already imports them or add them).

Remove the old 今日需要做的 card (which was the CTA pointing to /signals).

- [x] **Step 4: Run tests, see them pass**

```bash
npm test -- Dashboard.signals
```

Expected: all 4 new tests pass.

- [x] **Step 5: Delete old Signals files**

```bash
git rm frontend/src/pages/Signals.tsx
git rm frontend/src/pages/__tests__/Signals.test.tsx
```

Run `npm test` to confirm full suite still green.

- [x] **Step 6: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/__tests__/Dashboard.signals.test.tsx
git commit -m "feat(dashboard): inline weekly action checklist from /signals"
```

(The Signals.tsx and Signals.test.tsx deletions are part of the same commit.)

---

## Task 2: Frontend — 把持仓（Portfolio）搬到 Dashboard

**Files:**
- Create: `frontend/src/pages/__tests__/Dashboard.holdings.test.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx` (inline Portfolio content, replace Top 5 with full table)
- Delete: `frontend/src/pages/Portfolio.tsx`

**Interfaces:**
- Dashboard's `当前持仓` card renders ALL holdings from `/api/portfolio.holdings` (not Top 5).
- Columns: `代码 | 名称 | 持仓数量 | 成本价 | 现价 | 市值 | 浮动盈亏` (7 columns).
- Empty state: `暂无持仓` when `holdings` is empty.
- The old `当前持仓（Top 5）` card is removed.

- [x] **Step 1: Write failing tests** — Create `Dashboard.holdings.test.tsx`:
  - Full holdings table renders 7 columns: mock with one holding `{code: 510300.XSHG, shares: 1300, cost_price: 4.0, current_price: 4.2, market_value: 5460, pnl: 260}`. Assert all 7 column headers appear AND all 7 values appear.
  - Multiple rows: mock 2-3 holdings, assert each row's code appears (not just Top 5).
  - Empty state: mock with `holdings: []`, assert `暂无持仓` renders.

- [x] **Step 2: Run tests, see them fail**

```bash
npm test -- Dashboard.holdings
```

Expected: suite fails (file doesn't exist or new tests fail).

- [x] **Step 3: Migrate Portfolio.tsx into Dashboard.tsx**

Open `frontend/src/pages/Portfolio.tsx` (85 lines). Read its source. Identify the holdings table rendering logic (the `<table>` with columns + the row mapper).

Copy into `frontend/src/pages/Dashboard.tsx` as a new `<section>` after the 今日调仓 card (or after 系统状态 — your call). Use `usePortfolio()` + `usePool()` for the name lookup (already used elsewhere in Dashboard).

Replace the old `当前持仓（Top 5）` card with the full-table version. Drop the `.slice(0, 5)` if present.

- [x] **Step 4: Run tests, see them pass**

```bash
npm test -- Dashboard.holdings
```

Expected: all tests pass.

- [x] **Step 5: Delete old Portfolio file**

```bash
git rm frontend/src/pages/Portfolio.tsx
```

Run `npm test` to confirm full suite still green.

- [x] **Step 6: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/__tests__/Dashboard.holdings.test.tsx
git commit -m "feat(dashboard): inline full holdings table from /portfolio"
```

---

## Task 3: Frontend — 路由清理 + 顶导简化为 2 项 + 测试收尾

**Files:**
- Modify: `frontend/src/__tests__/app-shell-wiring.test.tsx` (2-entry nav assertion)
- Modify: `frontend/src/components/AppShell.tsx` (TOP_NAV: 4 → 2 entries)
- Modify: `frontend/src/App.tsx` (remove 3 routes)
- Modify: `frontend/src/pages/__tests__/Dashboard.test.tsx` (remove CTA assertions if any)
- Delete: `frontend/src/__tests__/screening-redirect.test.tsx`

**Interfaces:**
- AppShell's `TOP_NAV` has 2 entries: `仪表盘` (to `/`) and `设置` (button). No `持仓` or `今日调仓`.
- App.tsx routes: `/`, `/pool`, `/themes`, `/strategy`, `/dynamic-pool`, `/backtest`, `/history`, `/datasource`, `*`. No `/signals`, `/portfolio`, `/screening`.
- Wildcard `*` → `/` catches everything (so old bookmarks degrade gracefully).

- [x] **Step 1: Update wiring test first (RED)**

Edit `frontend/src/__tests__/app-shell-wiring.test.tsx`:
- Replace `expect(screen.getByText("持仓")).toBeInTheDocument();` with `expect(screen.queryByText("持仓")).not.toBeInTheDocument();`
- Replace `expect(screen.getByText("今日调仓")).toBeInTheDocument();` with `expect(screen.queryByText("今日调仓")).not.toBeInTheDocument();`
- Keep `expect(screen.getByText("仪表盘")).toBeInTheDocument();` and `expect(screen.getByText("设置")).toBeInTheDocument();`

Run `npm test -- app-shell-wiring` and confirm RED.

- [x] **Step 2: Update AppShell TOP_NAV**

In `frontend/src/components/AppShell.tsx`:
- Find the `TOP_NAV` constant (or the nav-entries array). Reduce from 4 entries to 2: keep `仪表盘` (path `/`) and `设置` (button). Remove `持仓` (path `/portfolio`) and `今日调仓` (path `/signals`).
- Update any prop types if the array length changed.

- [x] **Step 3: Remove routes from App.tsx**

In `frontend/src/App.tsx`:
- Delete `<Route path="/signals" element={<Signals />} />`
- Delete `<Route path="/portfolio" element={<Portfolio />} />`
- Delete `<Route path="/screening" element={<Navigate to="/signals" replace />} />`
- Also delete the `import Signals` and `import Portfolio` lines (now unused).
- Keep the wildcard `<Route path="*" element={<Navigate to="/" replace />} />`.

- [x] **Step 4: Run wiring test, see it pass**

```bash
npm test -- app-shell-wiring
```

Expected: GREEN.

- [x] **Step 5: Clean up obsolete tests**

- Delete `frontend/src/__tests__/screening-redirect.test.tsx` (route `/screening` no longer exists; wildcard handles it).
- Edit `frontend/src/pages/__tests__/Dashboard.test.tsx`: remove any assertion that checks for "CTA → /signals" or "CTA → /portfolio" links (those CTAs no longer exist in Dashboard).
- Verify `frontend/src/pages/__tests__/Dashboard.stale-sync.test.tsx` is unaffected (it only checks stale banner behavior).

Run `npm test` and confirm full suite passes.

- [x] **Step 6: Verify zero references**

```bash
cd frontend/src && git grep -n "/signals\|/portfolio\|/screening" || echo "OK: zero references"
```

Expected: `OK: zero references`. (Comments in deleted files shouldn't show up; spec docs are in `openspec/` and `docs/`, not `frontend/src/`.)

- [x] **Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/AppShell.tsx \
        frontend/src/__tests__/app-shell-wiring.test.tsx \
        frontend/src/pages/__tests__/Dashboard.test.tsx
git rm frontend/src/__tests__/screening-redirect.test.tsx
git commit -m "feat(shell): drop /signals, /portfolio, /screening routes and 2 top-nav entries"
```

---

## Task 4: Docs sync

- [x] **Step 1: Update `spec/requirements.md`**

After the `## 用户旅程重整（user-journey-reorg 2026-06-29）` section, add a new section `## Dashboard 化整为零（dashboard-flatten 2026-06-29）` documenting the IA simplification (no /signals, no /portfolio, no /screening; top nav 仪表盘 + 设置).

- [x] **Step 2: Update `spec/devlog.md`**

Append a `## dashboard-flatten 变更归档` entry following the same format as previous M-entries (date, branch, scope, key artifacts, CI verification, known limits).

- [x] **Step 3: Commit**

```bash
git add spec/devlog.md spec/requirements.md
git commit -m "chore(dashboard-flatten): sync project-level spec"
```

---

## Final verification

- [x] **Step 1: All CI green**

```bash
cd frontend && npm test && npm run lint && npm run build
cd ../backend && uv run pytest -q && uv run ruff check
```

- [x] **Step 2: Manual smoke**

The user can navigate to `/` and see Dashboard with full weekly action checklist AND full holdings table inline. No top-nav links to /signals or /portfolio exist. Settings sidebar still works.

- [x] **Step 3: Merge**

```bash
cd /Users/zane/Workspace/etf-momentum
git checkout main
git merge --ff-only feature/dashboard-flatten
# Verify CI still green after merge
git branch -d feature/dashboard-flatten
```
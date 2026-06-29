# User-Journey Reorganization — Design

**Date:** 2026-06-29
**Status:** Approved (awaiting implementation planning)
**Branch (when implementation begins):** `feature/user-journey-reorg`
**Parent:** `main`

## 1. Background

The current frontend has 10 routes registered against a single flat top nav
(`frontend/src/App.tsx:13-22`). All pages have equal visual weight, regardless of
how often the user needs them. This has produced four concrete chaos symptoms:

1. **`/screening` is registered as a route but absent from the nav** — the page
   is reachable only by typing the URL. Users cannot find it.
2. **The label "静态池" implies a sibling "动态池", but no such nav entry
   exists** — the dynamic pool lives buried under `/datasource`.
3. **The root `/` is a duplicate of the nav** — it just lists the same links,
   providing no daily-useful summary.
4. **No progressive disclosure** — daily-decision pages (portfolio, signals,
   data-source health) sit next to configuration and tooling pages with no
   hierarchy.

## 2. User persona

| Persona | Frequency | Primary need |
|---------|-----------|--------------|
| **Non-investor daily user** | Daily | "Am I up or down today? Do I need to do anything?" |
| **Non-investor weekly user** | Weekly | "What specific trades should I make?" |
| **System admin / debugger** | Rare | "Is the data source healthy?" |

The non-investor persona drives the IA — they are the daily touchpoint user.
Configuration, backtest, and data-source administration exist for them but
should not dominate the UI.

## 3. IA & route map

### 3.1 Top-level routes

| Old | New | Notes |
|-----|-----|-------|
| `/` (link list) | `/` → **Dashboard** | Real daily home |
| `/portfolio` | `/portfolio` (unchanged URL) | Now in main nav |
| `/signals` | `/signals` → **今日调仓** (action checklist) | Same URL, transformed UI |
| `/screening` | **REMOVED + redirect** | `Navigate replace` → `/signals` |
| `/backtest`, `/history`, `/datasource`, `/pool`, `/themes`, `/strategy` | All moved **only into Settings sidebar**; URLs unchanged |

`/dynamic-pool` is a **new** URL: it is promoted from a sub-page of `/datasource`
into a standalone route. `/datasource` keeps working but no longer hosts the
dynamic-pool UI.

### 3.2 Settings sidebar contents (in display order)

```
设置
  ├── 静态池            /pool           (config)
  ├── 主题词典          /themes         (config)
  ├── 策略参数          /strategy       (config)
  ├── 动态池            /dynamic-pool   (config)
  ├── ─────── divider ───────
  ├── 回测              /backtest       (tools)
  ├── 历史数据          /history        (tools)
  └── 数据源            /datasource     (tools)
```

### 3.3 Top-nav entries (4 total)

| Label | Path | Purpose |
|-------|------|---------|
| 仪表盘 | `/` | Daily home, 4 cards |
| 持仓 | `/portfolio` | Full holdings detail |
| 今日调仓 | `/signals` | Weekly rebalance action checklist |
| 设置 | (drawer trigger) | Opens the 8-entry left sidebar |

### 3.4 Sidebar behavior

- Default state: closed
- One click on "设置" opens a left drawer with the 8 entries above
- Active entry is highlighted
- Clicking outside or pressing Escape closes the drawer
- Drawer is a controlled component; URL does not change when opening/closing

## 4. Dashboard composition (`/`)

### 4.1 Layout (vertical scroll, 4 cards)

```
┌──────────────────────────────────────────────────────────────────┐
│ 📊 资产概览                                                        │
│  总市值 ¥XX,XXX   成本 ¥XX,XXX   浮动盈亏 ±¥X,XXX ±X.XX%           │
└──────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────┐ ┌─────────────────────────────┐
│ ⚡ 今日需要做的                    │ │  系统状态                    │
│   今天需要做 3 项调整             │ │   数据源  ● 在线             │
│   [ 查看清单 → /signals ]        │ │   缓存    128/204 hit       │
│   ─ 备选 ─                        │ │   动态池  12 已启用          │
│   今日不需要调整 ✓               │ │   上次同步  18:43            │
└─────────────────────────────────┘ └─────────────────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│ 📋 当前持仓（Top 5）                                               │
│  [ table ]                                                         │
│  [ 查看全部持仓 → /portfolio ]                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Card states

| Card | Conditions | UI behavior |
|------|------------|-------------|
| 资产概览 | portfolio 200 | Render total_market_value / total_cost / total_pnl / available_cash / net_value from `usePortfolio()` |
| 资产概览 | portfolio 5xx | "持仓数据暂不可用" + retry button |
| 今日需要做的 | signal non-empty, not all defensive | Show "N 项操作" + CTA |
| 今日需要做的 | signal empty / all defensive | "今日不需要调整 ✓" |
| 今日需要做的 | screening 5xx | "信号暂不可用" + link to /settings/data-source |
| 当前持仓 | portfolio 200 | Render 5 rows + link |
| 当前持仓 | portfolio has 0 holdings | "暂无持仓" + onboard link to /settings/pool |
| 系统状态 | source = fixture | Yellow tag "模拟数据中" + admin link |
| 系统状态 | dynamic_pool stale > 24h | Yellow warning + 立即同步 button |
| 系统状态 | /api/health down | Red dot + "未连接" |

### 4.3 Background jobs

- React Query parallelizes the 4 endpoint calls (cards fetch independently)
- Each card has its own loading skeleton; the page header does NOT block on data
- Re-fetch interval: 30s for non-critical cards (dashboard polls slower than /signals at 5s)
- No background mutations

### 4.4 Out of scope for v1

- 30-day net-value sparkline (v1.1)
- Real-time WebSocket updates
- Multi-account view

## 5. Signal page transformation (`/signals`)

### 5.1 Goal

Convert the existing raw field-dump page (`frontend/src/pages/Signals.tsx:1-84`)
into a copy-paste weekly to-do list a non-investor can execute at a broker.

### 5.2 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ 📌 今日调仓 · 2026-06-29（周一）                                  │
│   本次需做 3 项操作（卖出 2 + 买入 1）     预计耗时 ~2 分钟         │
│   信号计算时间：今日 14:50    数据源：akshare (缓存命中 8/10)  ✓   │
│   [ ▶ 进阶：为什么这样选 ]                                       │
│   [ ▶ 原始筛选输出 ]                                             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ 🔴 要卖出的 (2)                                                   │
│   代码       名称         当前持仓    卖出数量    估算金额          │
│   510500    中证500ETF    800 份      全部       ~¥3,120           │
│   小计:                                                ~¥5,095   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ 🟢 要买入的 (1)                                                   │
│   代码       名称         目标金额     买入数量                        │
│   510300    沪深300ETF   ¥5,095     1,300 份                  │
│   小计:                                                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ ⚠ 防御模式（仅触发时显示）                                         │
│   本次未发现满足条件的标的，资金转入 511880 银华日利               │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 Section behavior

| Section | Visible when | Render source |
|---------|--------------|---------------|
| 要卖出 / 要买入 | Always (or empty state) | Group `signals` by `type` |
| 估算金额 | holdings + `available_cash` available | `market_value` (SELL) / `target_value` (BUY) |
| 防御模式 | `signals` has BUY with `reason == "无动量目标，切换防御模式"` | Show banner |
| 进阶 | Click expand | Per-ETF: 动量分, MA, 量比 (from `/api/screening/today` join) |
| 原始输出 | Click expand | JSON dump of `useScreeningToday()` |

### 5.4 Copy & print

- Each row has inline "📋 复制" → copies `卖出 510500 中证500ETF 800 份`
- Global "📋 复制完整调仓清单" → copies multi-line text in broker-friendly format:
  ```
  卖出 510500 中证500ETF 800 份
  卖出 159915 创业板ETF 500 份
  买入 510300 沪深300ETF 1300 份
  ```
- `@media print` stylesheet: hide top nav, sidebar, and collapse all expanded sections → produces a one-page checklist PDF

### 5.5 Edge states

| Condition | UI |
|-----------|-----|
| `useSignalsToday` 5xx | Page replaces with "今日信号暂不可用" + link to data source |
| Last sync > 24h ago (from `daily_sync` metadata) | Yellow banner "信号可能过期" + 重新同步 link |
| Signal time outside 09:30–15:00 (off-hours) | Banner "本次信号基于 [date] 收盘，今日尚未更新" |

## 6. Pre-implementation investigation (already complete)

| Question | Finding | Implication |
|----------|---------|-------------|
| Does `/api/signals/today` already return action plan? | **YES** — `SignalOut` has `type/etf/reason/shares/target_value/market_value/pnl` | Pure frontend refactor for /signals. No new endpoint. |
| Does `/api/portfolio` have cash balance? | **NO** — only market_value/cost/pnl + holdings | Backend must add `available_cash` + `net_value` to `PortfolioResponse`. |
| Does `<Sidebar>` component exist? | **NO** — `frontend/src/components/` directory missing | Create from scratch. |
| Does `/api/dynamic-pool` exist? | **YES** — `/api/configs/pool/dynamic` | Promotion to `/dynamic-pool` is frontend-only. |

## 7. Implementation plan

### 7.1 Phased commits

Each commit must leave the tree shippable and pass CI.

| # | Scope | Files affected | Verifiable by |
|---|-------|----------------|---------------|
| 1 | Backend: extend `PortfolioResponse` with `available_cash` + `net_value`. Update `signals_today` to take cash from portfolio (remove 100k fallback). | `backend/app/api/screening.py`, `backend/app/services/signals.py`, tests | `pytest`; manual curl |
| 2 | Frontend: create `frontend/src/components/` with `Sidebar.tsx`, `Nav.tsx`, `AppShell.tsx`. Refactor `App.tsx` to use shell with 4 top entries + collapsible sidebar. All old URLs preserved. | `frontend/src/App.tsx` (rewrite), `frontend/src/components/*.tsx` (new), `frontend/src/pages/*.tsx` (untouched) | `npm run build`; smoke test all old URLs |
| 3 | Frontend: create `Dashboard.tsx`. Move dashboard cards layout from §4. Reuse existing hooks; no new fetches. | `frontend/src/pages/Dashboard.tsx` (new), `App.tsx` (route update) | Manual: dashboard renders 4 cards |
| 4 | Frontend: refactor `Signals.tsx` into action checklist per §5. Reuse existing hooks + new `usePortfolio` for cash field. | `frontend/src/pages/Signals.tsx` (rewrite), print stylesheet | Snapshot test of action table |
| 5 | Frontend: extract `DynamicPoolPage.tsx` from current `DataSource.tsx`. Add `/dynamic-pool` route + sidebar entry. `/datasource` keeps working. | `frontend/src/pages/DynamicPoolPage.tsx` (new), `DataSource.tsx` (slimmer), `App.tsx`, `Sidebar.tsx` | Smoke test both routes |
| 6 | Frontend: add `<Navigate replace>` for `/screening` → `/signals`. Remove `/screening` from nav (already not present). | `frontend/src/App.tsx` | curl `/screening` returns 200 → redirects |
| 7 | Frontend: edge-state polish — stale-data banner, copy buttons, print stylesheet, Chinese display-name resolution via `load_display_names` (already exposed). | `Signals.tsx`, `Dashboard.tsx`, `frontend/src/index.css` | Manual + Playwright smoke |

### 7.2 Backend API additions

```python
# backend/app/api/screening.py — PortfolioResponse
class PortfolioResponse(BaseModel):
    as_of: date_type
    total_market_value: float
    total_cost: float
    total_pnl: float
    available_cash: float          # NEW: 100_000 - total_cost
    net_value: float               # NEW: total_market_value + available_cash
    holdings: list[PortfolioHoldingOut]
```

```python
# backend/app/services/signals.py — remove 100k fallback
# Before:
total_value=total_value if total_value > 0 else 100_000.0,
# After:
total_value=portfolio_cash + portfolio.total_market_value,
```

### 7.3 Migration / backward compatibility

- **No DB schema change** — only an additive Pydantic model change
- **No URL removals** — `/screening` redirects, `/datasource` works
- **No breaking frontend changes** — existing hooks continue to work; the new
  `available_cash` / `net_value` fields are additive in `PortfolioResponse` (frontend must be updated to consume them, but the absence does not break old code since the old code never referenced these fields)
- **State file impact** — none; this is a new iteration; old active_change `akshare-code-normalization` already in merge

### 7.4 Testing strategy

| Layer | Tool | Coverage |
|-------|------|----------|
| Backend: `available_cash` + `net_value` | pytest | Schema; correct arithmetic; signals consume from portfolio (no 100k fallback) |
| Sidebar / Nav / AppShell | Vitest + RTL | Renders 4 top entries; sidebar has 8 items; active highlight |
| Dashboard cards | Vitest + RTL | loading / empty / populated / error states per card |
| Action checklist rows | Vitest + RTL | SELL/BUY rendered from `useSignalsToday`; defensive banner; copy buttons |
| Dynamic-pool split | Vitest + RTL | New URL renders the extracted page; old URL still works |
| /screening redirect | Vitest + RTL | `<Navigate>` triggers; final URL is `/signals` |
| E2E | Playwright (optional) | `/` → 设置 → /pool → /signals, one-click nav |
| Manual QA | checklist | Real data: copy checklist → broker app → paste → verify |
| CI | `tsc --noEmit`, `npm run build`, `pytest`, `ruff` | all green |

### 7.5 Out of scope (intentional)

- Mobile-native app
- Multi-user auth
- Real broker integration (剪贴板 only)
- Real-time WebSocket
- 30-day net-value chart (deferred to v1.1)
- Light/dark theme toggle (already-built only)
- Multi-language (Chinese only)

### 7.6 Open risks (must track during implementation)

1. **Stale-data timestamp source**: the "信号可能过期" banner needs a "last
   computed" timestamp. Currently `/api/signals/today` returns `as_of` (the
   market date), not a "last computed at" time. If unavailable, this UX must
   use `as_of` with a comparison to today's date.
2. **Chinese display-name lookup on dashboard**: the dashboard's holdings table
   needs `display_name` for each holding. The current `/api/portfolio` returns
   only `code`. Resolution: pre-fetch `/api/configs/pool/static` once at app
   load and build a name map client-side.
3. **Sidebar drawer on mobile screens (≤ 640px)**: the drawer may cover content
   awkwardly on small screens. Verify on Playwright mobile viewport.

## 8. Acceptance criteria

The change is "done" when all of the following hold:

1. `npm run build` and `tsc --noEmit` and `pytest` and `ruff check` all pass on `main`.
2. `frontend/src/App.tsx` shows exactly 4 top-nav entries.
3. `frontend/src/components/Sidebar.tsx` exists and renders 8 entries when opened.
4. Visiting `/` shows the 4 dashboard cards (per §4), each handling its loading / empty / error states.
5. Visiting `/signals` shows the action checklist (per §5), with copy-to-clipboard working.
6. Visiting `/screening` redirects to `/signals`.
7. `PortfolioResponse` includes `available_cash` and `net_value`; their correctness is covered by tests.
8. The 100k fallback in `signals_today` is removed; tests confirm signals are computed from actual cash + holdings.
9. All previous nav URLs (`/pool`, `/themes`, `/strategy`, `/portfolio`, `/backtest`, `/history`, `/datasource`, `/dynamic-pool`) still resolve.

## 9. References

- `frontend/src/App.tsx:13-22` — current nav
- `frontend/src/pages/Signals.tsx:1-84` — current signals page (raw dumps)
- `frontend/src/api/hooks.ts:215-221` — `useSignalsToday`
- `frontend/src/api/hooks.ts:207-213` — `usePortfolio`
- `backend/app/api/screening.py:128-190` — SignalOut shape
- `backend/app/services/signals.py:39-118` — signal generation logic
- `backend/app/services/portfolio_mock.py:21-25` — mock initial capital 100k
- `spec/requirements.md:44-55` — data-source + normalization requirements (unrelated but adjacent)

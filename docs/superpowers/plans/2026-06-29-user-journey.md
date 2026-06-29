# User-Journey Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the frontend IA around the non-investor daily user persona — a 4-entry top nav plus a collapsible Settings sidebar, a real dashboard at `/`, an action-checklist `/signals`, and a `/screening` redirect.

**Architecture:**
1. One small backend API extension: `PortfolioResponse.available_cash` + `net_value` (and remove the 100k fallback in `signals_today`).
2. Frontend gains a new `AppShell` (top nav) and `Sidebar` (collapsible drawer) component layer; pages inherit from `AppShell`.
3. The root `/` becomes a 4-card Dashboard. `/signals` becomes an action checklist. `/screening` redirects to `/signals`. `/dynamic-pool` is promoted out of `/datasource` into its own URL.

**Tech Stack:**
- Backend: FastAPI 0.115+, SQLModel, Pydantic v2, pytest, ruff
- Frontend: React 18.3, Vite 5.4, TypeScript 5.6, React Router 6, TanStack Query 5, Tailwind 3.4
- Frontend tests (NEW): Vitest 2.1 + @testing-library/react 16 + jsdom
- Existing patterns: snake_case Python, camelCase TS, Tailwind utility classes, default-export page components

**Branch:** `feature/user-journey-reorg` (cut from `main`)

**Spec reference:** `docs/superpowers/specs/2026-06-29-user-journey-design.md`

## Global Constraints

- TDD discipline: failing test → run to verify failure → minimal implementation → run to verify pass → commit. No exceptions.
- Every commit must leave all CI green: `cd backend && pytest -q && ruff check`, `cd frontend && tsc --noEmit && npm run build`.
- All current routes must still work (`/pool`, `/themes`, `/strategy`, `/portfolio`, `/backtest`, `/history`, `/datasource`); only nav visibility changes.
- No DB schema change. No new Pydantic model — additive field on existing model is the only backend change.
- Chinese display names: pre-fetch `/api/configs/pool` once at app load; build a `code → display_name` map client-side. (Existing hook `usePool` already returns these.)
- Mock initial capital is `100_000 RMB` per `backend/app/services/portfolio_mock.py`.
- Naming: new components use PascalCase filenames; new hooks use camelCase with `use` prefix.

## File Structure

### New files (frontend)

| Path | Responsibility |
|------|----------------|
| `frontend/src/components/AppShell.tsx` | Top nav (4 entries) + sidebar trigger; wraps page content |
| `frontend/src/components/Sidebar.tsx` | Collapsible left drawer; 8 entries; controlled by parent |
| `frontend/src/pages/Dashboard.tsx` | 4-card daily summary at `/` |
| `frontend/src/pages/DynamicPoolPage.tsx` | Promoted-out dynamic-pool UI (extracted from `DataSource.tsx`) |
| `frontend/src/pages/__tests__/Dashboard.test.tsx` | Dashboard card state coverage |
| `frontend/src/components/__tests__/AppShell.test.tsx` | Top nav rendering |
| `frontend/src/components/__tests__/Sidebar.test.tsx` | Sidebar entry list |
| `frontend/src/pages/__tests__/Signals.test.tsx` | Action checklist rendering |
| `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx` | Extraction preserves behavior |
| `frontend/src/__tests__/screening-redirect.test.tsx` | Navigate replace triggers |
| `vitest.config.ts` (in `frontend/`) | Vitest configuration (separate from vite.config.ts) |

### Modified files

| Path | Change |
|------|--------|
| `backend/app/api/screening.py` | Add 2 fields to `PortfolioResponse`; remove 100k fallback in `signals_today` |
| `frontend/src/App.tsx` | Use `AppShell`; register `/`, `/signals`, `/dynamic-pool`, `/screening` redirect |
| `frontend/src/pages/Signals.tsx` | Rewrite as action checklist per spec §5 |
| `frontend/src/pages/DataSource.tsx` | Remove dynamic-pool section (now in `DynamicPoolPage.tsx`) |
| `frontend/src/api/hooks.ts` | Extend `Portfolio` type with `available_cash` + `net_value` |
| `frontend/src/index.css` | Add `@media print` rules for clean checklist output |
| `frontend/package.json` | Add devDependencies for vitest + RTL + jsdom |
| `frontend/tsconfig.json` | Add `"types": ["vitest/globals", "@testing-library/jest-dom"]` |

### Untouched

- `frontend/src/main.tsx`, `frontend/src/index.css` (rules only appended), existing `pages/PoolConfig.tsx`, `pages/ThemeConfig.tsx`, `pages/StrategyConfig.tsx`, `pages/Backtest.tsx`, `pages/History.tsx`, `pages/Portfolio.tsx`
- All existing `backend/tests/*` files; new tests are additive.

---

## Task 1: Add Vitest + React Testing Library to frontend

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/tsconfig.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/setup.test.ts`

**Why first:** every subsequent UI task is TDD-driven. Get the harness running before writing any UI.

**Interfaces:**
- `npm run test` runs vitest in CI mode (`vitest run`)
- `npm run test:watch` runs vitest in watch mode
- `src/test/setup.ts` runs before each test file (extends matchers, registers jsdom)

- [ ] **Step 1: Install dev dependencies**

Run from `frontend/`:
```bash
npm install --save-dev vitest@^2.1.0 @vitest/ui@^2.1.0 \
  @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.5.0 \
  @testing-library/user-event@^14.5.0 jsdom@^25.0.0
```

Expected: package.json gains those deps; `node_modules/` is updated. No "peer dep missing" warnings.

- [ ] **Step 2: Add scripts to package.json**

In `frontend/package.json`, replace the `"scripts"` block with:
```json
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "tsc --noEmit",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
```

- [ ] **Step 3: Create vitest.config.ts**

Create `frontend/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
```

- [ ] **Step 4: Create test setup file**

Create `frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 5: Extend tsconfig.json**

In `frontend/tsconfig.json`, add `"types": ["vitest/globals", "@testing-library/jest-dom"]` to the `compilerOptions` object (alongside existing options like `"strict": true`).

Final `compilerOptions` block should include:
```json
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"],
    "baseUrl": ".",
```

- [ ] **Step 6: Write a smoke test**

Create `frontend/src/test/setup.test.ts`:
```ts
import { describe, expect, it } from "vitest";

describe("test harness", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 7: Run the smoke test**

Run from `frontend/`:
```bash
npm test
```

Expected: 1 test passes; output contains `✓ src/test/setup.test.ts`.

- [ ] **Step 8: Run `tsc --noEmit` to verify TypeScript**

Run:
```bash
npm run lint
```

Expected: no errors. The new `types` array must not conflict with the existing `bundler` moduleResolution.

- [ ] **Step 9: Commit**

```bash
cd frontend
git add package.json package-lock.json tsconfig.json vitest.config.ts src/test/
git commit -m "test(frontend): add vitest + react testing library"
```

---

## Task 2: Backend — extend PortfolioResponse with `available_cash` and `net_value`

**Files:**
- Modify: `backend/app/api/screening.py:79-122`
- Modify: `frontend/src/api/hooks.ts:37-43`
- Create: `backend/tests/test_portfolio_cash.py`

**Interfaces:**
- `PortfolioResponse.available_cash: float` — equals `100_000 − total_cost`
- `PortfolioResponse.net_value: float` — equals `total_market_value + available_cash`
- `signals_today()` computes `total_value` from `available_cash + total_market_value` (no more 100k fallback)

- [ ] **Step 1: Write failing test for cash fields**

Create `backend/tests/test_portfolio_cash.py`:
```python
"""Tests for portfolio cash fields and signal computation without fallback."""
from __future__ import annotations

import sys
import types
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.db import get_engine, init_db
from app.main import app


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    from app import db as db_module
    db_module.reset_engine_for_tests()
    init_db()
    # Prevent akshare or real network calls during startup
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        types.ModuleType("akshare"),
    )
    yield
    db_module.reset_engine_for_tests()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_portfolio_response_includes_available_cash_and_net_value(
    client: TestClient,
) -> None:
    """GET /api/portfolio must return available_cash and net_value.
    available_cash = 100_000 - total_cost (initial mock capital is 100k).
    net_value = total_market_value + available_cash.
    """
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()

    # New fields exist
    assert "available_cash" in body
    assert "net_value" in body

    # Both are numeric
    assert isinstance(body["available_cash"], (int, float))
    assert isinstance(body["net_value"], (int, float))

    # Arithmetic check
    total_cost = body["total_cost"]
    total_market_value = body["total_market_value"]
    assert body["available_cash"] == pytest.approx(100_000 - total_cost, abs=0.01)
    assert body["net_value"] == pytest.approx(
        total_market_value + body["available_cash"], abs=0.01
    )


def test_signals_endpoint_does_not_fall_back_to_100k(
    client: TestClient,
) -> None:
    """When total_value would be 0 (defensive case), signals must NOT silently
    use 100_000. The fallback is removed; cash is sourced from portfolio."""
    resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    # Each BUY signal must have target_value >= 0 (no crash)
    for sig in body["signals"]:
        if sig["type"] == "BUY":
            assert sig.get("target_value") is not None
            assert sig["target_value"] >= 0
```

- [ ] **Step 2: Run new tests, see them fail**

```bash
cd backend
pytest tests/test_portfolio_cash.py -v
```

Expected: `available_cash` and `net_value` are missing → `KeyError` → both tests FAIL.

- [ ] **Step 3: Add fields to `PortfolioResponse`**

Modify `backend/app/api/screening.py`:
- In `PortfolioResponse` (line 79), add after `total_pnl`:
```python
    available_cash: float
    net_value: float
```
- In `portfolio()` (line 87), after the `total_pnl` line in the return statement (line 119-121), add:
```python
        available_cash=round(100_000.0 - total_cost, 2),
        net_value=round(total_market_value + (100_000.0 - total_cost), 2),
```

The full return should now read:
```python
    return PortfolioResponse(
        as_of=as_of.date(),
        total_market_value=round(total_market_value, 2),
        total_cost=round(total_cost, 2),
        total_pnl=round(total_market_value - total_cost, 2),
        available_cash=round(100_000.0 - total_cost, 2),
        net_value=round(total_market_value + (100_000.0 - total_cost), 2),
        holdings=rows,
    )
```

- [ ] **Step 4: Update frontend `Portfolio` type**

In `frontend/src/api/hooks.ts`, replace the `Portfolio` type (lines 37-43):
```ts
export type Portfolio = {
  as_of: string;
  total_market_value: number;
  total_cost: number;
  total_pnl: number;
  available_cash: number;
  net_value: number;
  holdings: PortfolioHolding[];
};
```

- [ ] **Step 5: Run pytest, see them pass**

```bash
cd backend
pytest tests/test_portfolio_cash.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Run all backend tests to confirm no regression**

```bash
pytest
```

Expected: previously-passing tests still pass. Existing tests do not reference `available_cash` / `net_value`, so they should be unaffected.

- [ ] **Step 7: Run ruff**

```bash
ruff check
```

Expected: clean.

- [ ] **Step 8: Commit**

```bash
cd backend
git add app/api/screening.py tests/test_portfolio_cash.py
git add frontend/src/api/hooks.ts
git commit -m "feat(portfolio): expose available_cash and net_value"

# The frontend edit is in a different directory; commit from root:
cd ..
git add backend/app/api/screening.py backend/tests/test_portfolio_cash.py frontend/src/api/hooks.ts
git commit -m "feat(portfolio): expose available_cash and net_value"
```

---

## Task 3: Frontend — `AppShell` component (4-entry top nav)

**Files:**
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/__tests__/AppShell.test.tsx`
- Modify (later, in Task 7): `frontend/src/App.tsx`

**Interfaces:**
- `<AppShell>{children}</AppShell>` — wraps page content with top nav
- Top nav: 4 entries — Dashboard (`/`), Portfolio (`/portfolio`), 今日调仓 (`/signals`), 设置 (drawer trigger)
- The 设置 button calls `onSettingsClick?: () => void` (provided by parent when sidebar is present)
- The full active-link logic uses `useLocation()` from `react-router-dom`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/__tests__/AppShell.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/AppShell";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell>
        <p>page body</p>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("renders the four top-nav entries", () => {
    renderAt("/");
    expect(screen.getByText("仪表盘")).toBeInTheDocument();
    expect(screen.getByText("持仓")).toBeInTheDocument();
    expect(screen.getByText("今日调仓")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });

  it("renders children in the main area", () => {
    renderAt("/");
    expect(screen.getByText("page body")).toBeInTheDocument();
  });

  it("links the top-nav entries to the right paths", () => {
    renderAt("/");
    const dashboardLink = screen.getByRole("link", { name: "仪表盘" });
    const portfolioLink = screen.getByRole("link", { name: "持仓" });
    const signalsLink = screen.getByRole("link", { name: "今日调仓" });
    expect(dashboardLink).toHaveAttribute("href", "/");
    expect(portfolioLink).toHaveAttribute("href", "/portfolio");
    expect(signalsLink).toHaveAttribute("href", "/signals");
  });

  it("renders the brand heading", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: "ETF Momentum" })).toBeInTheDocument();
  });

  it("calls onSettingsClick when the settings trigger is clicked", async () => {
    const user = (await import("@testing-library/user-event")).default;
    const onClick = vi.fn();
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppShell onSettingsClick={onClick}>
          <p>x</p>
        </AppShell>
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: "设置" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
cd frontend
npm test -- AppShell
```

Expected: all 5 tests FAIL — `AppShell` module doesn't exist.

- [ ] **Step 3: Implement AppShell**

Create `frontend/src/components/AppShell.tsx`:
```tsx
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

const TOP_NAV: ReadonlyArray<{ to: string; label: string }> = [
  { to: "/", label: "仪表盘" },
  { to: "/portfolio", label: "持仓" },
  { to: "/signals", label: "今日调仓" },
];

interface AppShellProps {
  children: ReactNode;
  onSettingsClick?: () => void;
}

export function AppShell({ children, onSettingsClick }: AppShellProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container flex h-14 items-center gap-6">
          <Link to="/" className="font-semibold">
            <h1 className="font-semibold">ETF Momentum</h1>
          </Link>
          <nav className="flex gap-4 text-sm">
            {TOP_NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                }
              >
                {n.label}
              </NavLink>
            ))}
            <button
              type="button"
              onClick={onSettingsClick}
              className="text-muted-foreground hover:text-foreground"
            >
              设置
            </button>
          </nav>
        </div>
      </header>
      <main className="container py-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 4: Run tests, see them pass**

```bash
npm test -- AppShell
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run `tsc --noEmit` and `npm run build`**

```bash
npm run lint && npm run build
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd frontend
git add src/components/AppShell.tsx src/components/__tests__/AppShell.test.tsx
git commit -m "feat(shell): add AppShell with 4-entry top nav"
```

---

## Task 4: Frontend — `Sidebar` component (collapsible settings drawer)

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/__tests__/Sidebar.test.tsx`

**Interfaces:**
- `<Sidebar open={bool} onClose={() => void} />` — controlled drawer
- 8 entries in fixed display order, with divider between config (4) and tools (3)
- Click on entry navigates AND calls `onClose()` to dismiss the drawer
- Click on backdrop or press `Escape` calls `onClose()`
- URL change does NOT toggle the drawer (parent controls `open`)

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/__tests__/Sidebar.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Sidebar } from "@/components/Sidebar";

function renderSidebar(props: { open: boolean; onClose?: () => void }) {
  return render(
    <MemoryRouter>
      <Sidebar {...props} />
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("renders 8 settings entries when open", () => {
    renderSidebar({ open: true });
    expect(screen.getByText("静态池")).toBeInTheDocument();
    expect(screen.getByText("主题词典")).toBeInTheDocument();
    expect(screen.getByText("策略参数")).toBeInTheDocument();
    expect(screen.getByText("动态池")).toBeInTheDocument();
    expect(screen.getByText("回测")).toBeInTheDocument();
    expect(screen.getByText("历史数据")).toBeInTheDocument();
    expect(screen.getByText("数据源")).toBeInTheDocument();
  });

  it("does not render entries when closed", () => {
    renderSidebar({ open: false });
    expect(screen.queryByText("静态池")).not.toBeInTheDocument();
  });

  it("navigates each entry to the right path", () => {
    renderSidebar({ open: true });
    expect(screen.getByRole("link", { name: "静态池" })).toHaveAttribute("href", "/pool");
    expect(screen.getByRole("link", { name: "动态池" })).toHaveAttribute("href", "/dynamic-pool");
    expect(screen.getByRole("link", { name: "数据源" })).toHaveAttribute("href", "/datasource");
  });

  it("calls onClose when an entry is clicked", async () => {
    const onClose = vi.fn();
    renderSidebar({ open: true, onClose });
    await userEvent.click(screen.getByRole("link", { name: "静态池" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", async () => {
    const onClose = vi.fn();
    renderSidebar({ open: true, onClose });
    await userEvent.click(screen.getByTestId("sidebar-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape is pressed", async () => {
    const onClose = vi.fn();
    renderSidebar({ open: true, onClose });
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
npm test -- Sidebar
```

Expected: all tests FAIL — `Sidebar` module doesn't exist.

- [ ] **Step 3: Implement Sidebar**

Create `frontend/src/components/Sidebar.tsx`:
```tsx
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

const CONFIG_ENTRIES = [
  { to: "/pool", label: "静态池" },
  { to: "/themes", label: "主题词典" },
  { to: "/strategy", label: "策略参数" },
  { to: "/dynamic-pool", label: "动态池" },
] as const;

const TOOL_ENTRIES = [
  { to: "/backtest", label: "回测" },
  { to: "/history", label: "历史数据" },
  { to: "/datasource", label: "数据源" },
] as const;

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const location = useLocation();

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        data-testid="sidebar-backdrop"
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/40"
      />
      <aside
        className="fixed left-0 top-0 z-50 h-full w-64 border-r bg-background shadow-lg"
        role="dialog"
        aria-label="设置"
      >
        <div className="flex h-14 items-center border-b px-4 font-semibold">设置</div>
        <nav className="flex flex-col p-2 text-sm">
          {CONFIG_ENTRIES.map((e) => (
            <SidebarLink key={e.to} to={e.to} label={e.label} active={location.pathname === e.to} onClose={onClose} />
          ))}
          <div className="my-2 border-t" />
          {TOOL_ENTRIES.map((e) => (
            <SidebarLink key={e.to} to={e.to} label={e.label} active={location.pathname === e.to} onClose={onClose} />
          ))}
        </nav>
      </aside>
    </>
  );
}

function SidebarLink({
  to,
  label,
  active,
  onClose,
}: {
  to: string;
  label: string;
  active: boolean;
  onClose: () => void;
}) {
  return (
    <Link
      to={to}
      onClick={onClose}
      className={
        "rounded px-3 py-2 " +
        (active ? "bg-accent text-accent-foreground" : "hover:bg-accent/50")
      }
    >
      {label}
    </Link>
  );
}
```

- [ ] **Step 4: Run tests, see them pass**

```bash
npm test -- Sidebar
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run lint + build**

```bash
npm run lint && npm run build
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd frontend
git add src/components/Sidebar.tsx src/components/__tests__/Sidebar.test.tsx
git commit -m "feat(shell): add Sidebar component (collapsible settings drawer)"
```

---

## Task 5: Frontend — `Dashboard` page (`/`)

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/__tests__/Dashboard.test.tsx`
- Modify: `frontend/src/App.tsx` — register `/` route (modify only the `<Routes>` block; the AppShell wiring is in Task 7)

**Interfaces:**
- Renders 4 cards: 资产概览, 今日需要做的, 系统状态, 当前持仓
- Reads from existing hooks: `usePortfolio()`, `useSignalsToday()`, `useHealthStats()`, `useDynamicPool()`
- For holdings-display names, uses `usePool()` to build `code → display_name` map
- Each card handles loading / empty / error independently

- [ ] **Step 1: Write failing tests (covers card states)**

Create `frontend/src/pages/__tests__/Dashboard.test.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/pages/Dashboard";

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <Dashboard />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the four card headings", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 95000,
        total_cost: 92000,
        total_pnl: 3000,
        available_cash: 8000,
        net_value: 103000,
        holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText("资产概览")).toBeInTheDocument());
    expect(screen.getByText("今日需要做的")).toBeInTheDocument();
    expect(screen.getByText("系统状态")).toBeInTheDocument();
    expect(screen.getByText("当前持仓")).toBeInTheDocument();
  });

  it("renders cash + pnl from portfolio response", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 95000,
        total_cost: 92000,
        total_pnl: 3000,
        available_cash: 8000,
        net_value: 103000,
        holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText(/¥103,000/)).toBeInTheDocument());
  });

  it("shows the action-call CTA when there are signals", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 95000,
        total_cost: 92000,
        total_pnl: 3000,
        available_cash: 8000,
        net_value: 103000,
        holdings: [],
      },
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [{ type: "BUY", etf: "510300.XSHG", reason: "今日新进目标", shares: 1300, target_value: 5095 }],
      },
      "/api/screening/today": { as_of: "2026-01-15", targets: ["510300.XSHG"] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/今天需要做 1 项操作/)).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: /查看清单/ })).toHaveAttribute("href", "/signals");
  });

  it("shows 'no action needed' when signals are empty", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 95000,
        total_cost: 92000,
        total_pnl: 3000,
        available_cash: 8000,
        net_value: 103000,
        holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText(/今日不需要调整/)).toBeInTheDocument());
  });

  it("renders an empty-state when there are no holdings", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 0,
        total_cost: 0,
        total_pnl: 0,
        available_cash: 100000,
        net_value: 100000,
        holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText(/暂无持仓/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
npm test -- Dashboard
```

Expected: tests FAIL — Dashboard module doesn't exist.

- [ ] **Step 3: Implement Dashboard**

Create `frontend/src/pages/Dashboard.tsx`:
```tsx
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { useDynamicPool, useHealthStats, usePool, usePortfolio, useSignalsToday } from "@/api/hooks";

function money(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(value);
}

function pct(numerator: number, denominator: number): string {
  if (!denominator) return "—";
  const v = (numerator / denominator) * 100;
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function Dashboard() {
  const portfolio = usePortfolio();
  const signals = useSignalsToday();
  const pool = usePool();
  const dynamicPool = useDynamicPool();
  const health = useHealthStats();

  const nameByCode = useMemo(() => {
    const map: Record<string, string> = {};
    for (const e of pool.data ?? []) {
      if (e.display_name) map[e.code] = e.display_name;
    }
    return map;
  }, [pool.data]);

  const realSignals = (signals.data?.signals ?? []).filter(
    (s) => !(s.type === "BUY" && s.reason === "无动量目标，切换防御模式"),
  );
  const actionCount = realSignals.length;

  return (
    <div className="space-y-4">
      {/* 资产概览 */}
      <section className="rounded border bg-card p-4">
        <h2 className="text-lg font-semibold">📊 资产概览</h2>
        {portfolio.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {portfolio.isError && <p className="text-sm text-red-600">持仓数据暂不可用</p>}
        {portfolio.data && (
          <dl className="mt-2 grid grid-cols-2 gap-2 text-sm md:grid-cols-5">
            <Stat label="净值" value={money(portfolio.data.net_value)} />
            <Stat label="总市值" value={money(portfolio.data.total_market_value)} />
            <Stat label="成本" value={money(portfolio.data.total_cost)} />
            <Stat label="浮动盈亏" value={money(portfolio.data.total_pnl)} tone={portfolio.data.total_pnl >= 0 ? "pos" : "neg"} />
            <Stat label="可用资金" value={money(portfolio.data.available_cash)} />
          </dl>
        )}
      </section>

      {/* 今日需要做的 + 系统状态 */}
      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded border bg-card p-4 md:col-span-2">
          <h2 className="text-lg font-semibold">⚡ 今日需要做的</h2>
          {signals.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
          {signals.isError && (
            <p className="text-sm text-red-600">
              信号暂不可用 <Link to="/datasource" className="underline">检查数据源</Link>
            </p>
          )}
          {signals.data && actionCount > 0 && (
            <div className="mt-2 space-y-2">
              <p className="text-sm">今天需要做 {actionCount} 项操作</p>
              <Link to="/signals" className="inline-block rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground">
                查看清单 →
              </Link>
            </div>
          )}
          {signals.data && actionCount === 0 && (
            <p className="mt-2 text-sm text-emerald-700">今日不需要调整 ✓</p>
          )}
        </section>

        <section className="rounded border bg-card p-4">
          <h2 className="text-lg font-semibold">系统状态</h2>
          {health.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
          {health.data && (
            <ul className="mt-2 space-y-1 text-sm">
              <li>
                数据源:{" "}
                {health.data.status === "ok" ? (
                  <span className="text-emerald-700">● 在线</span>
                ) : (
                  <span className="text-red-600">● 未连接</span>
                )}
              </li>
              {health.data.cache_hit !== undefined && (
                <li>
                  缓存: {health.data.cache_hit}/{health.data.cache_miss !== undefined ? (health.data.cache_hit + health.data.cache_miss) : 0} hit
                </li>
              )}
              {dynamicPool.data && (
                <li>
                  动态池: {dynamicPool.data.filter((d) => d.is_enabled).length} 已启用 /{" "}
                  {dynamicPool.data.length} 总数
                </li>
              )}
              {dynamicPool.data && dynamicPool.data.length > 0 && (
                <li className="text-xs text-muted-foreground">
                  上次同步:{" "}
                  {new Date(dynamicPool.data[0].last_synced_at).toLocaleString("zh-CN")}
                </li>
              )}
            </ul>
          )}
          <Link to="/datasource" className="mt-2 inline-block text-xs underline">
            进入 →
          </Link>
        </section>
      </div>

      {/* 当前持仓 */}
      <section className="rounded border bg-card p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">📋 当前持仓（Top 5）</h2>
          {portfolio.data && portfolio.data.holdings.length > 0 && (
            <Link to="/portfolio" className="text-sm underline">查看全部持仓 →</Link>
          )}
        </div>
        {portfolio.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {portfolio.data && portfolio.data.holdings.length === 0 && (
          <p className="mt-2 text-sm text-muted-foreground">暂无持仓</p>
        )}
        {portfolio.data && portfolio.data.holdings.length > 0 && (
          <table className="mt-2 w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th>代码</th><th>名称</th><th>现价</th><th>数量</th><th>浮盈亏</th><th>比例</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.data.holdings.slice(0, 5).map((h) => (
                <tr key={h.code} className="border-t">
                  <td className="font-mono">{h.code}</td>
                  <td>{nameByCode[h.code] ?? "—"}</td>
                  <td>¥{h.current_price.toFixed(2)}</td>
                  <td>{h.shares.toLocaleString()}</td>
                  <td className={h.pnl >= 0 ? "text-emerald-700" : "text-red-600"}>
                    {money(h.pnl)}
                  </td>
                  <td className={h.pnl >= 0 ? "text-emerald-700" : "text-red-600"}>
                    {pct(h.pnl, h.cost_price * h.shares)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "pos" | "neg" }) {
  const toneClass = tone === "pos" ? "text-emerald-700" : tone === "neg" ? "text-red-600" : "";
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={`text-lg font-medium ${toneClass}`}>{value}</dd>
    </div>
  );
}

export default Dashboard;
```

- [ ] **Step 4: Run tests, see them pass**

```bash
npm test -- Dashboard
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Register `/` route in `App.tsx` (preliminary)**

Open `frontend/src/App.tsx`. In the `<Routes>` block, replace the existing `/` route:

Before:
```tsx
<Route path="/" element={<Landing />} />
```

After:
```tsx
<Route path="/" element={<Dashboard />} />
```

Also add `Dashboard` to the imports at top of the file:
```tsx
import { Dashboard } from "@/pages/Dashboard";
```

(The `Landing` component and unused `NAV` array get cleaned up in Task 7 when AppShell wiring lands.)

- [ ] **Step 6: Run lint + build**

```bash
npm run lint && npm run build
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd frontend
git add src/pages/Dashboard.tsx src/pages/__tests__/Dashboard.test.tsx src/App.tsx
git commit -m "feat(dashboard): new Dashboard page at / with 4 cards"
```

---

## Task 6: Frontend — `Signals` action checklist (`/signals`)

**Files:**
- Modify: `frontend/src/pages/Signals.tsx` (rewrite)
- Create: `frontend/src/pages/__tests__/Signals.test.tsx`

**Interfaces:**
- Action table columns:
  - SELL: 代码 | 名称 | 当前持仓 | 卖出数量 | 估算金额
  - BUY: 代码 | 名称 | 目标金额 | 买入数量
- Each row has inline `📋 复制` button → copies `卖出 510500 中证500ETF 800 份`-style string
- Global `📋 复制完整调仓清单` button → multi-line text
- Defensive banner when only BUY is the defensive ETF (`reason === "无动量目标，切换防御模式"`)
- Empty state when no signals

- [ ] **Step 1: Write failing tests**

Create `frontend/src/pages/__tests__/Signals.test.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Signals from "@/pages/Signals";

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderSignals() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <Signals />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Signals action checklist", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("groups signals into 卖出 / 买入 sections", async () => {
    setupFetchMock({
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [
          { type: "SELL", etf: "510500.XSHG", reason: "不在今日目标列表", shares: 800, market_value: 3120, pnl: 120 },
          { type: "BUY", etf: "510300.XSHG", reason: "今日新进目标", shares: 1300, target_value: 5095 },
        ],
      },
      "/api/screening/today": { as_of: "2026-01-15", targets: ["510300.XSHG"] },
    });
    renderSignals();
    await waitFor(() => expect(screen.getByText("要卖出的")).toBeInTheDocument());
    expect(screen.getByText("要买入的")).toBeInTheDocument();
    expect(screen.getByText("510500.XSHG")).toBeInTheDocument();
    expect(screen.getByText("510300.XSHG")).toBeInTheDocument();
  });

  it("shows defensive banner when only defensive BUY exists", async () => {
    setupFetchMock({
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [
          { type: "SELL", etf: "510300.XSHG", reason: "不在今日目标列表", shares: 1300, market_value: 5095, pnl: 195 },
          { type: "BUY", etf: "511880.XSHG", reason: "无动量目标，切换防御模式", shares: 5000, target_value: 21000 },
        ],
      },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
    });
    renderSignals();
    await waitFor(() => expect(screen.getByText(/防御模式/)).toBeInTheDocument());
  });

  it("shows empty state when there are no signals", async () => {
    setupFetchMock({
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
    });
    renderSignals();
    await waitFor(() => expect(screen.getByText(/今天没有需要做的/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
npm test -- Signals
```

Expected: tests FAIL — current `Signals.tsx` is the raw-card version; test expects new structure.

- [ ] **Step 3: Rewrite `Signals.tsx` as action checklist**

Replace the contents of `frontend/src/pages/Signals.tsx` with:
```tsx
import { useMemo } from "react";

import { useScreeningToday, useSignalsToday } from "@/api/hooks";

const DEFENSIVE_REASON = "无动量目标，切换防御模式";

export default function Signals() {
  const signals = useSignalsToday();
  const screening = useScreeningToday();

  const data = signals.data;
  const sellList = useMemo(() => (data?.signals ?? []).filter((s) => s.type === "SELL"), [data]);
  const buyList = useMemo(() => (data?.signals ?? []).filter((s) => s.type === "BUY"), [data]);
  const isDefensive = buyList.length === 1 && buyList[0].reason === DEFENSIVE_REASON;

  if (signals.isLoading) return <p>加载中…</p>;
  if (signals.isError) {
    return (
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">今日调仓</h2>
        <div className="rounded border border-rose-300 bg-rose-50 p-4 text-sm text-rose-900">
          今日信号暂不可用，请检查<a href="/datasource" className="underline">数据源</a>。
        </div>
      </section>
    );
  }
  if (!data) return null;

  const totalActions = sellList.length + buyList.length;

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">📌 今日调仓 · {data.as_of}</h2>
        {totalActions === 0 ? (
          <p className="mt-1 text-sm text-emerald-700">今天没有需要做的 ✓</p>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">
            本次需做 {totalActions} 项操作（卖出 {sellList.length} + 买入 {buyList.length}）
          </p>
        )}
      </header>

      {sellList.length > 0 && (
        <ActionTable
          title={`🔴 要卖出的 (${sellList.length})`}
          tone="sell"
          rows={sellList.map((s) => ({
            code: s.etf,
            name: s.etf,
            label: `卖出 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`,
            cols: {
              "当前持仓": `${(s.shares ?? 0).toLocaleString()} 份`,
              "卖出数量": "全部",
              "估算金额": formatMoney(s.market_value),
            },
          }))}
        />
      )}

      {buyList.length > 0 && (
        <ActionTable
          title={`🟢 要买入的 (${buyList.length})`}
          tone="buy"
          rows={buyList.map((s) => ({
            code: s.etf,
            name: s.etf,
            label: `买入 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`,
            cols: {
              "目标金额": formatMoney(s.target_value),
              "买入数量": `${(s.shares ?? 0).toLocaleString()} 份`,
            },
          }))}
        />
      )}

      {isDefensive && (
        <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          ⚠ 本次未发现满足条件的标的，资金转入 <code>511880.XSHG</code> 银华日利
        </div>
      )}

      <details className="rounded border p-2 text-sm">
        <summary className="cursor-pointer">▶ 原始筛选输出</summary>
        <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(screening.data, null, 2)}</pre>
      </details>
    </section>
  );
}

function formatMoney(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(v);
}

interface ActionRow {
  code: string;
  name: string;
  label: string;
  cols: Record<string, string>;
}

function ActionTable({
  title,
  tone,
  rows,
}: {
  title: string;
  tone: "buy" | "sell";
  rows: ActionRow[];
}) {
  const headerClass = tone === "buy"
    ? "border-emerald-300 bg-emerald-50"
    : "border-rose-300 bg-rose-50";

  return (
    <div className={`rounded border p-3 ${headerClass}`}>
      <h3 className="mb-2 text-sm font-medium">{title}</h3>
      <table className="w-full text-sm">
        <thead className="text-left text-xs opacity-70">
          <tr>
            <th>代码</th>
            {Object.keys(rows[0].cols).map((h) => (
              <th key={h}>{h}</th>
            ))}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.code} className="border-t border-current/10">
              <td className="font-mono">{r.code}</td>
              {Object.entries(r.cols).map(([k, v]) => (
                <td key={k}>{v}</td>
              ))}
              <td>
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(r.label)}
                  className="text-xs underline"
                >
                  📋 复制
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run tests, see them pass**

```bash
npm test -- Signals
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run lint + build**

```bash
npm run lint && npm run build
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd frontend
git add src/pages/Signals.tsx src/pages/__tests__/Signals.test.tsx
git commit -m "feat(signals): transform /signals into copy-paste weekly checklist"
```

---

## Task 7: Frontend — extract `DynamicPoolPage` and add `/dynamic-pool` route

**Files:**
- Create: `frontend/src/pages/DynamicPoolPage.tsx` (extracted from `DataSource.tsx`)
- Modify: `frontend/src/pages/DataSource.tsx` (remove dynamic-pool section)
- Modify: `frontend/src/App.tsx` (add `/dynamic-pool` route)
- Modify: `frontend/src/components/Sidebar.tsx` (already links to `/dynamic-pool` from Task 4)

**Interfaces:**
- `<DynamicPoolPage />` renders the same UI the old `DataSource.tsx` had for the dynamic-pool section (sync button, list with toggles)
- `/dynamic-pool` route renders `<DynamicPoolPage />`
- `/datasource` keeps working but no longer hosts dynamic pool

- [ ] **Step 1: Inspect the existing `DataSource.tsx` to copy the dynamic-pool block**

Open `frontend/src/pages/DataSource.tsx`. Identify the section that uses `useDynamicPool`, `useSyncDynamicPool`, `useToggleDynamicEntry`. Copy that JSX block.

- [ ] **Step 2: Write failing test for the extracted page**

Create `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DynamicPoolPage from "@/pages/DynamicPoolPage";

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <DynamicPoolPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("DynamicPoolPage", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders the dynamic pool heading", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/动态池/)).toBeInTheDocument());
  });

  it("renders an empty state when no rows", async () => {
    setupFetchMock({ "/api/configs/pool/dynamic": [] });
    renderPage();
    await waitFor(() => expect(screen.getByText(/暂无条目/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 3: Run tests, see them fail**

```bash
npm test -- DynamicPoolPage
```

Expected: tests FAIL — module doesn't exist.

- [ ] **Step 4: Create DynamicPoolPage**

Create `frontend/src/pages/DynamicPoolPage.tsx` with the dynamic-pool JSX block copied from `DataSource.tsx`. The component must:
- Use `useDynamicPool()` to fetch and poll
- Show a "重新同步" button that calls `useSyncDynamicPool().mutate`
- Render rows with code, name, last_synced_at, and an is_enabled toggle that calls `useToggleDynamicEntry().mutate`
- Default export

Skeleton (replace internals with what you copied):
```tsx
import { useDynamicPool, useSyncDynamicPool, useToggleDynamicEntry } from "@/api/hooks";

export default function DynamicPoolPage() {
  const { data, isLoading, isError } = useDynamicPool();
  const sync = useSyncDynamicPool();
  const toggle = useToggleDynamicEntry();

  if (isLoading) return <p>加载中…</p>;
  if (isError) return <p className="text-red-600">加载失败</p>;

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">动态池</h2>
        <button
          type="button"
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
          className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {sync.isPending ? "同步中…" : "重新同步"}
        </button>
      </header>

      {data && data.length === 0 && <p className="text-sm text-muted-foreground">暂无条目，请点击「重新同步」</p>}

      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th>代码</th><th>名称</th><th>启用</th><th>上次同步</th>
            </tr>
          </thead>
          <tbody>
            {data.map((e) => (
              <tr key={e.code} className="border-t">
                <td className="font-mono">{e.code}</td>
                <td>{e.name}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={e.is_enabled}
                    onChange={(ev) =>
                      toggle.mutate({ code: e.code, isEnabled: ev.target.checked })
                    }
                  />
                </td>
                <td className="text-xs text-muted-foreground">
                  {new Date(e.last_synced_at).toLocaleString("zh-CN")}
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

(Adjust the empty-state text to match whatever your test assertion uses; the test uses `/暂无条目/` so the above string works.)

- [ ] **Step 5: Run tests, see them pass**

```bash
npm test -- DynamicPoolPage
```

Expected: both tests PASS.

- [ ] **Step 6: Slim down `DataSource.tsx`**

Open `frontend/src/pages/DataSource.tsx`. Remove the dynamic-pool section (the JSX block you copied in Step 1). Keep the rest of `DataSource.tsx` intact (cache stats, health card, sync metadata).

- [ ] **Step 7: Register `/dynamic-pool` route**

In `frontend/src/App.tsx`, after the existing imports, add:
```tsx
import DynamicPoolPage from "@/pages/DynamicPoolPage";
```

In `<Routes>`, add a new route above `/datasource`:
```tsx
<Route path="/dynamic-pool" element={<DynamicPoolPage />} />
```

- [ ] **Step 8: Run lint + build + all tests**

```bash
npm run lint && npm run build && npm test
```

Expected: all green. Old `/datasource` URL still works (it still imports DataSource; we just removed a sub-section).

- [ ] **Step 9: Commit**

```bash
git add src/pages/DynamicPoolPage.tsx src/pages/__tests__/DynamicPoolPage.test.tsx \
        src/pages/DataSource.tsx src/App.tsx
git commit -m "feat(pool): promote dynamic pool to its own /dynamic-pool route"
```

---

## Task 8: Frontend — `/screening` redirect

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/__tests__/screening-redirect.test.tsx`

**Interfaces:**
- Visiting `/screening` triggers `<Navigate to="/signals" replace />` and renders `<Signals />`

- [ ] **Step 1: Write failing test**

Create `frontend/src/__tests__/screening-redirect.test.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderAppAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("/screening redirect", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders /signals content when /screening is visited", async () => {
    setupFetchMock({
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
    });
    renderAppAt("/screening");
    await waitFor(() => expect(screen.getByText(/今日调仓/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
npm test -- screening-redirect
```

Expected: test FAILS — `/screening` is registered as `<Screening />` today.

- [ ] **Step 3: Replace `/screening` route with `<Navigate>`**

Open `frontend/src/App.tsx`. Add to imports at top:
```tsx
import { Link, Navigate, Route, Routes } from "react-router-dom";
```

In `<Routes>`, replace the existing `<Route path="/screening" ... />` line with:
```tsx
<Route path="/screening" element={<Navigate to="/signals" replace />} />
```

Also remove the unused `Screening` import (line 6 of original) since we no longer need the page module.

- [ ] **Step 4: Delete the old `Screening.tsx` file**

```bash
rm frontend/src/pages/Screening.tsx
rmdir frontend/src/pages/__tests__ 2>/dev/null || true
```

(After Task 5, the `__tests__` directory should already exist alongside `pages/`; the `rmdir` is a no-op.)

- [ ] **Step 5: Run tests, see them pass**

```bash
npm test -- screening-redirect
```

Expected: PASS.

- [ ] **Step 6: Run full test suite + lint + build**

```bash
npm test && npm run lint && npm run build
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/__tests__/screening-redirect.test.tsx src/App.tsx src/pages/Screening.tsx
git commit -m "feat(routing): redirect /screening to /signals"
```

(`Screening.tsx` is in the commit as a deletion.)

---

## Task 9: Wire `AppShell` + `Sidebar` into `App.tsx` and remove old `Landing` / `NAV`

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- The full app wraps content in `<AppShell>` and provides `<Sidebar>` via `useState`
- The old `<Landing>` page and the old `NAV` constant are deleted
- Route list: `/`, `/portfolio`, `/signals`, `/pool`, `/themes`, `/strategy`, `/dynamic-pool`, `/backtest`, `/history`, `/datasource`, plus the `/screening` redirect

- [ ] **Step 1: Write failing test for the wired shell**

Create `frontend/src/__tests__/app-shell-wiring.test.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderApp(initialPath: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("App shell wiring", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders the 4-entry top nav", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 0, total_cost: 0, total_pnl: 0,
        available_cash: 100000, net_value: 100000, holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderApp("/");
    await waitFor(() => expect(screen.getByText("仪表盘")).toBeInTheDocument());
    expect(screen.getByText("持仓")).toBeInTheDocument();
    expect(screen.getByText("今日调仓")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });

  it("opens the sidebar when 设置 is clicked", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 0, total_cost: 0, total_pnl: 0,
        available_cash: 100000, net_value: 100000, holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderApp("/");
    await waitFor(() => expect(screen.getByText("仪表盘")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "设置" }));
    expect(screen.getByText("静态池")).toBeInTheDocument();
    expect(screen.getByText("主题词典")).toBeInTheDocument();
    expect(screen.getByText("动态池")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
npm test -- app-shell-wiring
```

Expected: tests FAIL — current `App.tsx` renders its own flat top nav, not the AppShell.

- [ ] **Step 3: Rewrite `App.tsx`**

Replace the entire contents of `frontend/src/App.tsx` with:
```tsx
import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { Sidebar } from "@/components/Sidebar";
import Backtest from "@/pages/Backtest";
import Dashboard from "@/pages/Dashboard";
import DataSource from "@/pages/DataSource";
import DynamicPoolPage from "@/pages/DynamicPoolPage";
import History from "@/pages/History";
import PoolConfig from "@/pages/PoolConfig";
import Portfolio from "@/pages/Portfolio";
import Signals from "@/pages/Signals";
import StrategyConfig from "@/pages/StrategyConfig";
import ThemeConfig from "@/pages/ThemeConfig";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <>
      <AppShell onSettingsClick={() => setSidebarOpen(true)}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/pool" element={<PoolConfig />} />
          <Route path="/themes" element={<ThemeConfig />} />
          <Route path="/strategy" element={<StrategyConfig />} />
          <Route path="/dynamic-pool" element={<DynamicPoolPage />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/history" element={<History />} />
          <Route path="/datasource" element={<DataSource />} />
          <Route path="/screening" element={<Navigate to="/signals" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
    </>
  );
}
```

- [ ] **Step 4: Run tests, see them pass**

```bash
npm test -- app-shell-wiring
```

Expected: both tests PASS.

- [ ] **Step 5: Run full test suite + lint + build**

```bash
npm test && npm run lint && npm run build
```

Expected: all green.

- [ ] **Step 6: Run backend tests**

```bash
cd ../backend && pytest -q && ruff check
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/src/App.tsx frontend/src/__tests__/app-shell-wiring.test.tsx
git commit -m "feat(shell): wire AppShell + Sidebar into top-level App"
```

---

## Task 10: Edge-state polish — print stylesheet + dashboard tile for stale sync

**Files:**
- Modify: `frontend/src/pages/Signals.tsx` (print-friendly `<article>` wrapping; ensure no animations)
- Modify: `frontend/src/index.css` (add `@media print` rules)
- Modify: `frontend/src/pages/Dashboard.tsx` (yellow banner when `dynamicPool.data[0].last_synced_at` older than 24h)

**Why:** The user-persona is non-investor. Print-friendly output and a clear "needs sync" warning are quick UX wins.

- [ ] **Step 1: Write failing test for stale-sync banner**

Create `frontend/src/pages/__tests__/Dashboard.stale-sync.test.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/pages/Dashboard";

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <Dashboard />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Dashboard stale-sync warning", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("shows a stale-sync warning when last synced > 24h ago", async () => {
    const staleDate = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 0, total_cost: 0, total_pnl: 0,
        available_cash: 100000, net_value: 100000, holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: staleDate },
      ],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText(/动态池已过期/)).toBeInTheDocument());
  });

  it("does not show the warning when last synced < 24h ago", async () => {
    const freshDate = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 0, total_cost: 0, total_pnl: 0,
        available_cash: 100000, net_value: 100000, holdings: [],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: freshDate },
      },
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.queryByText(/动态池已过期/)).not.toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run tests, see them fail**

```bash
npm test -- Dashboard.stale-sync
```

Expected: tests FAIL — Dashboard does not yet render the warning.

- [ ] **Step 3: Add the stale-sync banner to Dashboard**

Open `frontend/src/pages/Dashboard.tsx`. In the 系统状态 section, find the "上次同步" line and replace it with the following logic (it computes the staleness and shows a banner above the system-status card when stale):

```tsx
const lastSync = dynamicPool.data && dynamicPool.data[0]?.last_synced_at
  ? new Date(dynamicPool.data[0].last_synced_at)
  : null;
const isStale = lastSync !== null && (Date.now() - lastSync.getTime() > 24 * 60 * 60 * 1000);
```

Then at the top of the system-status card JSX, prepend:
```tsx
{isStale && (
  <div className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
    ⚠ 动态池已过期（&gt;24h），建议 <Link to="/dynamic-pool" className="underline">立即同步</Link>
  </div>
)}
```

- [ ] **Step 4: Add `@media print` stylesheet for Signals**

Open `frontend/src/index.css` and append:
```css
@media print {
  header nav,
  aside,
  details {
    display: none !important;
  }
  main {
    padding: 0 !important;
  }
}
```

- [ ] **Step 5: Run tests, see them pass**

```bash
npm test -- Dashboard.stale-sync
```

Expected: both tests PASS.

- [ ] **Step 6: Run full test + lint + build**

```bash
npm test && npm run lint && npm run build
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/__tests__/Dashboard.stale-sync.test.tsx frontend/src/index.css
git commit -m "feat(ux): stale-sync warning on dashboard + print stylesheet"
```

---

## Final verification

After all 10 tasks complete, run from project root:

- [ ] **Step 1: All CI green**

```bash
cd backend && pytest -q && ruff check
cd ../frontend && npm test && npm run lint && npm run build
```

- [ ] **Step 2: Manual end-to-end smoke**

```bash
cd .. && bash scripts/dev.sh  # or: backend uvicorn + frontend npm run dev
# Visit:
#   http://localhost:5173/           -> Dashboard with 4 cards
#   /signals                         -> action checklist
#   /screening                       -> redirects to /signals
#   /pool, /themes, /strategy, /backtest, /history, /datasource -> all reachable from 设置 sidebar
#   /dynamic-pool                    -> standalone dynamic pool UI
```

- [ ] **Step 3: Update project-level spec**

Edit `spec/devlog.md` to add a new M11 entry summarizing this change, following the format of M9/M10 entries.

- [ ] **Step 4: Sync spec files**

```bash
# From project root
./openspec sync  # if OpenSpec is configured
# Or manually: ensure spec/requirements.md reflects any new data shape changes
```

- [ ] **Step 5: Commit final state**

```bash
git add spec/devlog.md spec/requirements.md
git commit -m "chore(user-journey-reorg): update project-level spec for M11"
```

---

## Self-Review Notes

**Spec coverage:**
| Spec section | Implemented by |
|--------------|----------------|
| §3 IA & route map | Tasks 3, 4, 5, 6, 7, 8, 9 |
| §3.4 Sidebar behavior | Task 4 |
| §4 Dashboard composition | Task 5 |
| §4.2 Card states | Task 5 (tests cover loading/empty/populated/error per card) |
| §5 Signal page transformation | Task 6 |
| §5.3 Section behavior | Task 6 |
| §5.4 Copy & print | Task 6 (copy buttons), Task 10 (print CSS) |
| §5.5 Edge states | Task 10 (stale-sync) |
| §6 Investigation findings | Task 2 (backend cash) |
| §7.1 Phased commits | Tasks 1–10 correspond |
| §7.2 Backend API additions | Task 2 |
| §7.6 Open risks (last-sync source) | Task 10 |
| §7.6 Open risks (display-name lookup) | Task 5 uses `usePool()` for names |
| §8 Acceptance criteria | Verified by Final verification |

**Placeholders found and fixed during self-review:** None — every code block above is complete.

**Type consistency check:**
- `Portfolio.available_cash` / `net_value` defined in Task 2 (backend + frontend types)
- `Signal` type already exists with `type/etf/reason/shares/target_value/market_value/pnl` — Task 6 uses verbatim (no field drift)
- `Sidebar` `CONFIG_ENTRIES` and `TOOL_ENTRIES` arrays exactly match Task 4 test expectations
- `DynamicPoolEntry` already exposes `code/name/is_enabled/last_synced_at` — Task 7 uses verbatim

**Out-of-scope verification:**
- No DB schema change ✓
- No new Pydantic models ✓ (additive on existing `PortfolioResponse`)
- No new dependencies beyond devDeps for testing ✓
- No real broker integration ✓
- Mobile native ✓ excluded
- Light/dark theme toggle ✓ excluded

**Ambiguity fixed during self-review:**
- §1 explicitly scopes the "测试框架" gap and resolves it by adding vitest+RTL in Task 1
- Step-by-step `available_cash = 100_000 - total_cost` is the single source of truth (no fragmenting into service layer changes)
- "Estimated last-sync age" uses `Date.now()` consistently across the codebase (jsdom polyfill not needed since the test date math is computed at render time)

**Known variance from spec, kept intentional:**
- Spec §4.3 calls for `Dashboard` re-fetch at 30s. The plan reuses existing hooks whose `refetchInterval` is `5_000` (kept from M9). The dashboard therefore polls every 5s, which is more responsive than the spec but harmless (no backend cost increase). Adjusting polling cadence is a 1-line follow-up and out of scope here.

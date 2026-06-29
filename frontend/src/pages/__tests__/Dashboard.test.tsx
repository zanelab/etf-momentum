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
    await waitFor(() => expect(screen.getByText(/今天没有需要做的/)).toBeInTheDocument());
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

  it("shows inline action table when there are signals", async () => {
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
      expect(screen.getByText(/本次需做 1 项操作/)).toBeInTheDocument(),
    );
    expect(screen.getByText("要买入的")).toBeInTheDocument();
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
    await waitFor(() => expect(screen.getByText(/今天没有需要做的/)).toBeInTheDocument());
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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEFENSIVE_REASON } from "@/api/hooks";
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

function basePortfolio() {
  return {
    as_of: "2026-01-15",
    total_market_value: 95000,
    total_cost: 92000,
    total_pnl: 3000,
    available_cash: 8000,
    net_value: 103000,
    holdings: [],
  };
}

describe("Dashboard inline action checklist", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders SELL table in 今日调仓 card with code and shares", async () => {
    setupFetchMock({
      "/api/portfolio": basePortfolio(),
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [
          { type: "SELL", etf: "510500.XSHG", reason: "不在今日目标列表", shares: 800, market_value: 2400, pnl: 120 },
        ],
      },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText("要卖出的")).toBeInTheDocument());
    expect(screen.getByText("510500.XSHG")).toBeInTheDocument();
    expect(screen.getByText("800 份")).toBeInTheDocument();
  });

  it("renders BUY table in 今日调仓 card with code and formatted target value", async () => {
    setupFetchMock({
      "/api/portfolio": basePortfolio(),
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [
          { type: "BUY", etf: "510300.XSHG", reason: "今日新进目标", shares: 1300, target_value: 5095 },
        ],
      },
      "/api/screening/today": { as_of: "2026-01-15", targets: ["510300.XSHG"] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText("要买入的")).toBeInTheDocument());
    expect(screen.getByText("510300.XSHG")).toBeInTheDocument();
    expect(screen.getByText("¥5,095")).toBeInTheDocument();
  });

  it("shows defensive banner when only defensive BUY exists", async () => {
    setupFetchMock({
      "/api/portfolio": basePortfolio(),
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [
          { type: "BUY", etf: "511880.XSHG", reason: DEFENSIVE_REASON, shares: 5000, target_value: 21000 },
        ],
      },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText(/防御模式/)).toBeInTheDocument());
  });

  it("shows empty state when there are no signals", async () => {
    setupFetchMock({
      "/api/portfolio": basePortfolio(),
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.getByText(/今天没有需要做的/)).toBeInTheDocument());
  });
});

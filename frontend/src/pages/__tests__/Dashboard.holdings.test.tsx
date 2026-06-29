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

describe("Dashboard inline holdings table", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders 7 columns and all 7 values for a single holding", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 5460,
        total_cost: 5200,
        total_pnl: 260,
        available_cash: 8000,
        net_value: 108000,
        holdings: [
          {
            code: "510300.XSHG",
            shares: 1300,
            cost_price: 4.0,
            current_price: 4.2,
            market_value: 5460,
            pnl: 260,
          },
        ],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [
        { code: "510300.XSHG", display_name: "沪深300ETF" },
      ],
    });
    renderDashboard();
    // Wait for portfolio data to render — cost_price "4.00" only appears in
    // the holdings table (not in the 资产概览 summary).
    await waitFor(() => expect(screen.getByText("4.00")).toBeInTheDocument());

    // 7 column headers. Some ("代码", "名称", "现价", "浮动盈亏") also appear
    // in other Dashboard cards, so we use getAllByText and verify presence.
    expect(screen.getAllByText("代码").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("名称").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("持仓数量")).toBeInTheDocument();
    expect(screen.getByText("成本价")).toBeInTheDocument();
    expect(screen.getAllByText("现价").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("市值")).toBeInTheDocument();
    expect(screen.getAllByText("浮动盈亏").length).toBeGreaterThanOrEqual(1);

    // All 7 values for the single holding
    expect(screen.getByText("510300.XSHG")).toBeInTheDocument();
    expect(screen.getByText("沪深300ETF")).toBeInTheDocument();
    expect(screen.getByText("1,300")).toBeInTheDocument();
    expect(screen.getByText("4.00")).toBeInTheDocument();
    expect(screen.getByText("4.20")).toBeInTheDocument();
    expect(screen.getAllByText("¥5,460")).toHaveLength(2);
    expect(screen.getAllByText("¥260")).toHaveLength(2);
  });

  it("renders every row when there are multiple holdings (not Top 5)", async () => {
    setupFetchMock({
      "/api/portfolio": {
        as_of: "2026-01-15",
        total_market_value: 15000,
        total_cost: 14000,
        total_pnl: 1000,
        available_cash: 5000,
        net_value: 110000,
        holdings: [
          { code: "510300.XSHG", shares: 1300, cost_price: 4.0, current_price: 4.2, market_value: 5460, pnl: 260 },
          { code: "510500.XSHG", shares: 800, cost_price: 5.5, current_price: 5.8, market_value: 4640, pnl: 240 },
          { code: "510880.XSHG", shares: 2000, cost_price: 2.3, current_price: 2.45, market_value: 4900, pnl: 300 },
        ],
      },
      "/api/signals/today": { as_of: "2026-01-15", signals: [] },
      "/api/screening/today": { as_of: "2026-01-15", targets: [] },
      "/api/health": { status: "ok" },
      "/api/configs/pool/dynamic": [],
      "/api/configs/pool": [
        { code: "510300.XSHG", display_name: "沪深300ETF" },
        { code: "510500.XSHG", display_name: "中证500ETF" },
        { code: "510880.XSHG", display_name: "红利ETF" },
      ],
    });
    renderDashboard();
    // Wait for the holdings table to render — cost_price "2.30" only appears
    // in the 3rd row.
    await waitFor(() => expect(screen.getByText("2.30")).toBeInTheDocument());
    // All three codes must appear — not just the first 5
    expect(screen.getByText("510300.XSHG")).toBeInTheDocument();
    expect(screen.getByText("510500.XSHG")).toBeInTheDocument();
    expect(screen.getByText("510880.XSHG")).toBeInTheDocument();
  });

  it("shows empty state (暂无持仓) when holdings list is empty", async () => {
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
    await waitFor(() => expect(screen.getByText("暂无持仓")).toBeInTheDocument());
  });
});
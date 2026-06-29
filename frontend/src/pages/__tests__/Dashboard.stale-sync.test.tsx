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
      ],
      "/api/configs/pool": [],
    });
    renderDashboard();
    await waitFor(() => expect(screen.queryByText(/动态池已过期/)).not.toBeInTheDocument());
  });
});
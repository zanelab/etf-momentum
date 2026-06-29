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

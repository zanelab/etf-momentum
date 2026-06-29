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

  it("shows global 复制完整调仓清单 button when there are signals", async () => {
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
    await waitFor(() => expect(screen.getByText(/复制完整/)).toBeInTheDocument());
  });

  it("renders 进阶：为什么这样选 details with rows from screening details", async () => {
    setupFetchMock({
      "/api/signals/today": {
        as_of: "2026-01-15",
        signals: [
          { type: "BUY", etf: "510300.XSHG", reason: "今日新进目标", shares: 1300, target_value: 5095 },
        ],
      },
      "/api/screening/today": {
        as_of: "2026-01-15",
        targets: ["510300.XSHG"],
        details: [
          { code: "510300.XSHG", momentum_score: 0.4321, annual_return: 0.18, r2: 0.8765, volume_ratio: 0.95 },
        ],
      },
      "/api/configs/pool": [
        { code: "510300.XSHG", display_name: "沪深300ETF", enabled: true },
      ],
    });
    renderSignals();
    await waitFor(() => expect(screen.getByText(/进阶：为什么这样选/)).toBeInTheDocument());
    // Annual return formatted as a percentage (18.00%) — appears inside the 进阶 table
    expect(screen.getByText("18.00%")).toBeInTheDocument();
  });
});

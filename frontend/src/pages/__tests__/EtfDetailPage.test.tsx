import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import EtfDetailPage from "@/pages/EtfDetailPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

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

function renderAt(initialPath: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <QueryClientProvider client={qc}>
        <Routes>
          <Route path="/dynamic-pool/:code" element={<EtfDetailPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("EtfDetailPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();
  });
  afterEach(() => vi.restoreAllMocks());

  it("renders in-pool ETF with title, back link, and chart", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/market/history": {
        code: "510300.XSHG",
        start: "2026-01-01",
        end: "2026-03-19",
        fields: ["open", "high", "low", "close", "volume"],
        rows: [
          { date: "2026-01-02", open: 3.8, high: 3.85, low: 3.78, close: 3.82, volume: 1_000_000 },
          { date: "2026-01-03", open: 3.82, high: 3.9, low: 3.81, close: 3.88, volume: 1_200_000 },
        ],
      },
    });
    renderAt("/dynamic-pool/510300.XSHG");
    await waitFor(() => {
      // title contains code + name
      expect(
        screen.getByRole("heading", { level: 2, name: /510300\.XSHG\s*·\s*沪深300ETF/ })
      ).toBeInTheDocument();
    });
    // back link exists
    expect(screen.getByText(/返回动态池/)).toBeInTheDocument();
    // recharts container rendered (ResponsiveContainer → .recharts-responsive-container)
    expect(document.querySelector(".recharts-responsive-container")).toBeTruthy();
  });

  it("renders soft-fallback banner for out-of-pool code", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/market/history": {
        code: "999999.XSHG",
        start: "2026-01-01",
        end: "2026-03-19",
        fields: ["open", "high", "low", "close", "volume"],
        rows: [
          { date: "2026-01-02", open: 1.0, high: 1.05, low: 0.99, close: 1.02, volume: 500_000 },
        ],
      },
    });
    renderAt("/dynamic-pool/999999.XSHG");
    await waitFor(() => {
      // amber soft fallback banner
      expect(screen.getByText(/不在动态池中/)).toBeInTheDocument();
      // chart still renders (both pool + history must resolve)
      expect(document.querySelector(".recharts-responsive-container")).toBeTruthy();
    });
    // back link still present
    expect(screen.getByText(/返回动态池/)).toBeInTheDocument();
  });

  it("back link navigates to /dynamic-pool", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/market/history": {
        code: "510300.XSHG",
        start: "2026-01-01",
        end: "2026-03-19",
        fields: ["open", "high", "low", "close", "volume"],
        rows: [{ date: "2026-01-02", open: 3.8, high: 3.85, low: 3.78, close: 3.82, volume: 1_000_000 }],
      },
    });
    renderAt("/dynamic-pool/510300.XSHG");
    const link = await waitFor(() => screen.getByText(/返回动态池/));
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("/dynamic-pool");
  });

  it("renders without crashing when history is empty", async () => {
    // No /api/market/history mock — hook will fetch but no response (404 default).
    // useMarketHistory has enabled: !!code, so it WILL fetch when code is set.
    // We mock the pool but leave history to fail; the page should still render
    // header + back link + fallback message, no crash.
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/market/history": {
        code: "510300.XSHG",
        start: "2026-01-01",
        end: "2026-03-19",
        fields: ["open", "high", "low", "close", "volume"],
        rows: [], // empty data
      },
    });
    renderAt("/dynamic-pool/510300.XSHG");
    // Header + back link present, no chart
    await waitFor(() => {
      expect(screen.getByText(/返回动态池/)).toBeInTheDocument();
    });
    expect(document.querySelector(".recharts-responsive-container")).toBeNull();
  });
});

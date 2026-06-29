import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DynamicPoolPage from "@/pages/DynamicPoolPage";

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
  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();
  });
  afterEach(() => vi.restoreAllMocks());

  it("renders the dynamic pool heading", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [] },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/动态池/)).toBeInTheDocument());
  });

  it("renders an empty state when no rows", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [],
      "/api/sync/historical/status": { as_of: null, etfs: [] },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/暂无动态池条目/)).toBeInTheDocument());
  });

  it("renders two sync buttons", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [] },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeInTheDocument();
  });

  it("second button is disabled when pool is empty", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [],
      "/api/sync/historical/status": { as_of: null, etfs: [] },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeDisabled();
    });
    expect(screen.getByRole("button", { name: "同步 ETF" })).not.toBeDisabled();
  });

  it("row click navigates to /dynamic-pool/:code", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [] },
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    fireEvent.click(row);
    expect(mockNavigate).toHaveBeenCalledWith("/dynamic-pool/510300.XSHG");
  });

  it("checkbox click does NOT navigate", async () => {
    const user = (await import("@testing-library/user-event")).default;
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [] },
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    const checkbox = row.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox).toBeTruthy();
    await user.click(checkbox);
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/configs/pool/dynamic/510300.XSHG",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

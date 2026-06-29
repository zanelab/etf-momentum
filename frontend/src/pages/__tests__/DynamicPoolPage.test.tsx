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
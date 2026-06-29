import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SyncStatus } from "@/pages/SyncStatus";

// URL-prefix fetch mock — matches each fetch call to the response whose key
// is a prefix of the URL. Used for tests that don't need ordering.
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

// Ordered fetch mock — replays a fixed sequence of (method+url-prefix → body)
// pairs. Needed for the trigger test where the same URL is hit twice with
// different data between calls.
function setupOrderedFetchMock(
  sequence: { method: string; urlPrefix: string; body: unknown }[],
) {
  let idx = 0;
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = (init?.method ?? "GET").toUpperCase();
    const current = sequence[idx++];
    if (!current) {
      return new Response("{}", { status: 500 });
    }
    if (method !== current.method || !url.startsWith(current.urlPrefix)) {
      return new Response("{}", { status: 500 });
    }
    return new Response(JSON.stringify(current.body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;
}

function renderSyncStatus() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <SyncStatus />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("SyncStatus page", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("renders sync status table with one row per ETF", async () => {
    setupFetchMock({
      "/api/sync/historical/status": {
        as_of: "2026-03-19",
        etfs: [
          { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-19", status: "ok", error: null },
          { code: "510500.XSHG", name: "中证500ETF", last_synced_date: "2026-03-19", status: "ok", error: null },
        ],
      },
    });
    renderSyncStatus();
    await waitFor(() => expect(screen.getByText("510300.XSHG")).toBeInTheDocument());
    expect(screen.getByText("510500.XSHG")).toBeInTheDocument();
    expect(screen.getAllByText("✓ 已同步").length).toBeGreaterThanOrEqual(1);
  });

  it("shows 暂无 ETF when pool is empty", async () => {
    setupFetchMock({
      "/api/sync/historical/status": { as_of: null, etfs: [] },
    });
    renderSyncStatus();
    await waitFor(() => expect(screen.getByText("暂无 ETF")).toBeInTheDocument());
  });

  it("clicking 立即同步 calls POST and updates the table", async () => {
    setupOrderedFetchMock([
      // 1) initial status fetch
      {
        method: "GET",
        urlPrefix: "/api/sync/historical/status",
        body: {
          as_of: "2026-03-19",
          etfs: [
            { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-19", status: "ok", error: null },
          ],
        },
      },
      // 2) manual trigger POST
      {
        method: "POST",
        urlPrefix: "/api/sync/historical/trigger",
        body: {
          as_of: "2026-03-20",
          etfs: [
            { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-20", status: "ok", error: null },
          ],
          synced_count: 1,
          run_at: "2026-03-20T10:00:00Z",
        },
      },
      // 3) refetch after trigger invalidates
      {
        method: "GET",
        urlPrefix: "/api/sync/historical/status",
        body: {
          as_of: "2026-03-20",
          etfs: [
            { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-20", status: "ok", error: null },
          ],
        },
      },
    ]);
    renderSyncStatus();
    await waitFor(() => expect(screen.getByText("510300.XSHG")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /立即同步/ }));
    await waitFor(() => expect(screen.getByText("2026-03-20")).toBeInTheDocument());
  });
});

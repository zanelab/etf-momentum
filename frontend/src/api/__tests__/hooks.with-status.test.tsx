import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDynamicPoolWithStatus } from "../hooks";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => vi.restoreAllMocks());

describe("useDynamicPoolWithStatus", () => {
  it("fetches /api/sync/historical/status once on mount", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          as_of: "2026-01-15",
          etfs: [
            {
              code: "510300.XSHG", name: "沪深300ETF",
              last_synced_date: null, last_synced_at: null,
              is_enabled: true, status: "never", error: null, progress: null,
            },
          ],
          in_progress: null,
          is_running: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useDynamicPoolWithStatus(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.is_running).toBe(false);
    expect(result.current.data?.etfs[0].code).toBe("510300.XSHG");
  });

  it("does not refetch when is_running=false (no polling)", async () => {
    let calls = 0;
    globalThis.fetch = vi.fn(async () => {
      calls += 1;
      return new Response(
        JSON.stringify({ as_of: null, etfs: [], in_progress: null, is_running: false }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useDynamicPoolWithStatus(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const initial = calls;
    await new Promise((r) => setTimeout(r, 100));
    expect(calls).toBe(initial);  // no extra calls
  });
});

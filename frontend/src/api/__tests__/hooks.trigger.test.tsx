import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useTriggerSync } from "../hooks";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useTriggerSync", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POSTs to /api/sync/historical/trigger with from_date and to_date query params", async () => {
    let capturedUrl: string | null = null;
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      capturedUrl = url;
      return new Response(
        JSON.stringify({
          as_of: "2024-04-21",
          etfs: [],
          in_progress: null,
          is_running: false,
          synced_count: 0,
          run_at: new Date().toISOString(),
          from_date: "2024-04-19",
          to_date: "2024-04-21",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      );
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useTriggerSync(), { wrapper });
    result.current.mutate({ from_date: "2024-04-19", to_date: "2024-04-21" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedUrl).not.toBeNull();
    expect(capturedUrl!).toContain("/api/sync/historical/trigger");
    expect(capturedUrl!).toContain("from_date=2024-04-19");
    expect(capturedUrl!).toContain("to_date=2024-04-21");
  });
});

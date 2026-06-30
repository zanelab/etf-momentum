import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCancelSync } from "../hooks";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCancelSync", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POSTs to /api/sync/historical/cancel and returns cancelled=true", async () => {
    let capturedUrl: string | null = null;
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      capturedUrl = url;
      return new Response(JSON.stringify({ cancelled: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useCancelSync(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedUrl).not.toBeNull();
    expect(capturedUrl!).toContain("/api/sync/historical/cancel");
    expect(result.current.data).toEqual({ cancelled: true });
  });
});

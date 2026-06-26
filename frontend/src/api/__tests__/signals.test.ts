import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchLatestSignals } from "@/api/signals";

describe("fetchLatestSignals", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls /api/v1/signals/latest and returns the parsed payload", async () => {
    const payload = {
      date: "2026-06-26",
      rows: [
        { etf_code: "510300", momentum_score: "0.1234", rank: 1, action: "BUY" },
        { etf_code: "510500", momentum_score: null, rank: null, action: "WATCH" },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchLatestSignals();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/signals/latest");
    expect(init).toEqual({ method: "GET", headers: { Accept: "application/json" } });
    expect(result).toEqual(payload);
  });

  it("propagates an empty snapshot as { date, rows: [] }", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ date: null, rows: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchLatestSignals();

    expect(result.rows).toEqual([]);
    expect(result.date).toBeNull();
  });

  it("throws ApiError when the backend returns a non-2xx status", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({ detail: "boom" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchLatestSignals()).rejects.toThrow("boom");
  });
});

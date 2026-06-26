import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchAllEtfs } from "@/api/etfs";

describe("fetchAllEtfs", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls /api/v1/etfs?limit=500 and returns the parsed payload", async () => {
    const payload = {
      items: [
        { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
        { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
      ],
      total: 2,
      limit: 500,
      offset: 0,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAllEtfs();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/etfs?limit=500");
    expect(result).toEqual(payload);
    expect(result.items).toHaveLength(2);
  });

  it("returns an empty list when the pool has no entries", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ items: [], total: 0, limit: 500, offset: 0 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAllEtfs();

    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });

  it("throws ApiError when the backend fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => ({ detail: "etfs down" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchAllEtfs()).rejects.toThrow("etfs down");
  });
});

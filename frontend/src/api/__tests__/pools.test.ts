import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createPool,
  deletePool,
  getPool,
  listPools,
  updatePool,
  type EtfPoolCreateRequest,
} from "@/api/pools";

const SAMPLE_REQUEST: EtfPoolCreateRequest = {
  name: "宽基核心",
  description: "沪深300+中证500",
  etf_codes: ["510300", "510500"],
};

const SAMPLE_DETAIL = {
  id: 1,
  name: "宽基核心",
  description: "沪深300+中证500",
  members: [
    {
      code: "510300",
      name: "沪深300ETF",
      market: "SH",
      category: "宽基",
      position: 0,
    },
    {
      code: "510500",
      name: "中证500ETF",
      market: "SH",
      category: "宽基",
      position: 1,
    },
  ],
  created_at: "2026-06-27T00:00:00",
  updated_at: "2026-06-27T00:00:00",
};

const SAMPLE_LIST = {
  items: [
    {
      id: 1,
      name: "宽基核心",
      description: "沪深300+中证500",
      member_count: 2,
      created_at: "2026-06-27T00:00:00",
      updated_at: "2026-06-27T00:00:00",
    },
  ],
  total: 1,
};

function mockJsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Bad Request",
    json: async () => body,
  };
}

describe("listPools", () => {
  afterEach(() => vi.restoreAllMocks());

  it("GETs /api/v1/pools and returns the parsed list", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(SAMPLE_LIST));
    vi.stubGlobal("fetch", fetchMock);

    const result = await listPools();

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/pools");
    expect(result).toEqual(SAMPLE_LIST);
  });

  it("returns an empty list when no pools exist", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(mockJsonResponse({ items: [], total: 0 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await listPools();
    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });

  it("surfaces network errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("NetworkError")),
    );
    await expect(listPools()).rejects.toThrow("NetworkError");
  });
});

describe("getPool", () => {
  afterEach(() => vi.restoreAllMocks());

  it("GETs /api/v1/pools/{id} and returns the detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(SAMPLE_DETAIL));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getPool(1);

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/pools/1");
    expect(result).toEqual(SAMPLE_DETAIL);
  });

  it("surfaces 404 with the backend detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockJsonResponse({ detail: "EtfPool 999 not found" }, false, 404),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPool(999)).rejects.toThrow("EtfPool 999 not found");
  });
});

describe("createPool", () => {
  afterEach(() => vi.restoreAllMocks());

  it("POSTs to /api/v1/pools and returns the detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(SAMPLE_DETAIL));
    vi.stubGlobal("fetch", fetchMock);

    const result = await createPool(SAMPLE_REQUEST);

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/pools");
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init).toMatchObject({ method: "POST" });
    expect(JSON.parse(init!.body as string)).toEqual(SAMPLE_REQUEST);
    expect(result).toEqual(SAMPLE_DETAIL);
  });

  it("surfaces 409 on duplicate name", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockJsonResponse({ detail: "Pool '宽基核心' already exists" }, false, 409),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(createPool(SAMPLE_REQUEST)).rejects.toThrow("already exists");
  });

  it("surfaces 422 on unknown etf_code", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockJsonResponse(
        { detail: "Unknown ETF codes: ['999999']" },
        false,
        422,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(createPool(SAMPLE_REQUEST)).rejects.toThrow("999999");
  });
});

describe("updatePool", () => {
  afterEach(() => vi.restoreAllMocks());

  it("PUTs to /api/v1/pools/{id} and returns the detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(SAMPLE_DETAIL));
    vi.stubGlobal("fetch", fetchMock);

    const result = await updatePool(1, SAMPLE_REQUEST);

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/pools/1");
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init).toMatchObject({ method: "PUT" });
    expect(JSON.parse(init!.body as string)).toEqual(SAMPLE_REQUEST);
    expect(result).toEqual(SAMPLE_DETAIL);
  });

  it("surfaces 409 on rename collision", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockJsonResponse({ detail: "Pool 'x' already exists" }, false, 409),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(updatePool(1, SAMPLE_REQUEST)).rejects.toThrow("already exists");
  });
});

describe("deletePool", () => {
  afterEach(() => vi.restoreAllMocks());

  it("DELETEs /api/v1/pools/{id} and resolves with undefined on 204", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 204, statusText: "No Content" });
    vi.stubGlobal("fetch", fetchMock);

    const result = await deletePool(1);

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/pools/1");
    expect(fetchMock.mock.calls[0]![1]).toMatchObject({ method: "DELETE" });
    expect(result).toBeUndefined();
  });
});

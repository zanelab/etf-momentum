import { afterEach, describe, expect, it, vi } from "vitest";

import { getBacktestNav, getBacktestRun, runBacktest, type BacktestRequest } from "@/api/backtest";

const SAMPLE_REQUEST: BacktestRequest = {
  etf_pool: ["510300", "510500"],
  start: "2025-01-01",
  end: "2025-12-31",
  initial_cash: "100000",
  lookback: 252,
  skip: 21,
  top_n: 5,
  rebalance_freq: "monthly",
};

const SAMPLE_RUN = {
  id: 7,
  name: null,
  etf_pool: ["510300", "510500"],
  momentum_window: 252,
  rebalance_freq: "monthly",
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  metrics: {
    total_return: "0.1234",
    annualized_return: "0.15",
    max_drawdown: "0.08",
    sharpe_ratio: "1.2",
    sortino_ratio: "1.5",
    calmar_ratio: "1.8",
  },
  created_at: "2025-12-31T00:00:00",
};

function mockJsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Bad Request",
    json: async () => body,
  };
}

describe("runBacktest", () => {
  afterEach(() => vi.restoreAllMocks());

  it("POSTs to /api/v1/backtest and returns the parsed BacktestRun", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(SAMPLE_RUN));
    vi.stubGlobal("fetch", fetchMock);

    const result = await runBacktest(SAMPLE_REQUEST);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/backtest");
    expect(init).toMatchObject({ method: "POST" });
    expect(JSON.parse(init!.body as string)).toEqual(SAMPLE_REQUEST);
    expect(result).toEqual(SAMPLE_RUN);
  });

  it("surfaces 422 validation errors", async () => {
    const detail = [
      { loc: ["body", "start"], msg: "start must be < end", type: "value_error" },
    ];
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse({ detail }, false, 422));
    vi.stubGlobal("fetch", fetchMock);

    await expect(runBacktest(SAMPLE_REQUEST)).rejects.toThrow("start must be < end");
  });

  it("surfaces network errors", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("NetworkError"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(runBacktest(SAMPLE_REQUEST)).rejects.toThrow("NetworkError");
  });
});

describe("getBacktestRun", () => {
  afterEach(() => vi.restoreAllMocks());

  it("GETs /api/v1/backtest/{id}", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(SAMPLE_RUN));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getBacktestRun(7);

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/backtest/7");
    expect(result).toEqual(SAMPLE_RUN);
  });
});

describe("getBacktestNav", () => {
  afterEach(() => vi.restoreAllMocks());

  it("GETs /api/v1/backtest/{id}/nav and returns the NAV series", async () => {
    const body = {
      id: 7,
      nav_series: [
        { date: "2025-01-01", nav: "100000" },
        { date: "2025-02-01", nav: "101500" },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getBacktestNav(7);

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/backtest/7/nav");
    expect(result.nav_series).toHaveLength(2);
  });

  it("returns an empty series when the run has no nav_series", async () => {
    const body = { id: 8, nav_series: [] };
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getBacktestNav(8);

    expect(result.nav_series).toEqual([]);
  });

  it("surfaces 404 with the backend detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockJsonResponse({ detail: "BacktestRun 999 not found" }, false, 404),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getBacktestNav(999)).rejects.toThrow("BacktestRun 999 not found");
  });
});

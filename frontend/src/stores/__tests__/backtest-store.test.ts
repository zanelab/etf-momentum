import { beforeEach, describe, expect, it, vi } from "vitest";

import * as backtestApi from "@/api/backtest";
import { ApiError } from "@/api/client";
import { useBacktestStore } from "@/stores/backtest-store";

const SAMPLE_REQUEST: backtestApi.BacktestRequest = {
  etf_pool: ["510300"],
  start: "2025-01-01",
  end: "2025-12-31",
  initial_cash: "100000",
  lookback: 252,
  skip: 21,
  top_n: 5,
  rebalance_freq: "monthly",
};

const SAMPLE_RUN: backtestApi.BacktestRun = {
  id: 7,
  name: null,
  etf_pool: ["510300"],
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

const SAMPLE_NAV: backtestApi.BacktestNavResponse = {
  id: 7,
  nav_series: [
    { date: "2025-01-01", nav: "100000" },
    { date: "2025-02-01", nav: "101500" },
  ],
};

describe("useBacktestStore", () => {
  beforeEach(() => {
    useBacktestStore.getState().reset();
    vi.restoreAllMocks();
  });

  it("starts in idle state with no run or nav", () => {
    const state = useBacktestStore.getState();
    expect(state.submitStatus).toBe("idle");
    expect(state.navStatus).toBe("idle");
    expect(state.currentRun).toBeNull();
    expect(state.navSeries).toEqual([]);
    expect(state.formErrors).toEqual({});
    expect(state.submitError).toBeNull();
    expect(state.navError).toBeNull();
  });

  it("transitions idle → loading → ok → loading-nav → nav-ok on success", async () => {
    const submitSpy = vi
      .spyOn(backtestApi, "runBacktest")
      .mockResolvedValue(SAMPLE_RUN);
    const navSpy = vi
      .spyOn(backtestApi, "getBacktestNav")
      .mockResolvedValue(SAMPLE_NAV);

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    const state = useBacktestStore.getState();
    expect(submitSpy).toHaveBeenCalledWith(SAMPLE_REQUEST);
    expect(navSpy).toHaveBeenCalledWith(7);
    expect(state.submitStatus).toBe("ok");
    expect(state.navStatus).toBe("ok");
    expect(state.currentRun).toEqual(SAMPLE_RUN);
    expect(state.navSeries).toEqual(SAMPLE_NAV.nav_series);
  });

  it("extracts field errors from 422 violations", async () => {
    const violations = [
      { loc: ["body", "start"], msg: "start must be < end", type: "value_error" },
      { loc: ["body", "etf_pool"], msg: "pool must not be empty", type: "value_error" },
    ];
    const apiError = new ApiError("validation failed", 422, violations);
    vi.spyOn(backtestApi, "runBacktest").mockRejectedValue(apiError);

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    const state = useBacktestStore.getState();
    expect(state.submitStatus).toBe("error");
    expect(state.formErrors).toEqual({
      start: "start must be < end",
      etf_pool: "pool must not be empty",
    });
    expect(state.currentRun).toBeNull();
    expect(state.navStatus).toBe("idle");
  });

  it("falls back to the 'form' key when a violation has no loc field", async () => {
    const apiError = new ApiError("validation failed", 422, [
      { msg: "general oops" },
    ]);
    vi.spyOn(backtestApi, "runBacktest").mockRejectedValue(apiError);

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    expect(useBacktestStore.getState().formErrors).toEqual({
      form: "general oops",
    });
  });

  it("treats non-422 errors as network-level failures", async () => {
    vi.spyOn(backtestApi, "runBacktest").mockRejectedValue(new Error("boom"));

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    const state = useBacktestStore.getState();
    expect(state.submitStatus).toBe("error");
    expect(state.submitError).toBe("boom");
    expect(state.formErrors).toEqual({});
  });

  it("leaves nav alone when submit fails and keeps nav idle", async () => {
    vi.spyOn(backtestApi, "runBacktest").mockRejectedValue(new Error("network"));
    const navSpy = vi.spyOn(backtestApi, "getBacktestNav");

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    expect(navSpy).not.toHaveBeenCalled();
    expect(useBacktestStore.getState().navStatus).toBe("idle");
  });

  it("sets navStatus=error when nav fetch fails after a successful submit", async () => {
    vi.spyOn(backtestApi, "runBacktest").mockResolvedValue(SAMPLE_RUN);
    vi.spyOn(backtestApi, "getBacktestNav").mockRejectedValue(new Error("nav down"));

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    const state = useBacktestStore.getState();
    expect(state.submitStatus).toBe("ok");
    expect(state.currentRun).toEqual(SAMPLE_RUN);
    expect(state.navStatus).toBe("error");
    expect(state.navError).toBe("nav down");
  });

  it("clear field errors and previous nav when a new submit starts", async () => {
    vi.spyOn(backtestApi, "runBacktest")
      .mockRejectedValueOnce(
        new ApiError("validation failed", 422, [
          { loc: ["body", "start"], msg: "bad start", type: "value_error" },
        ]),
      )
      .mockResolvedValueOnce(SAMPLE_RUN);
    vi.spyOn(backtestApi, "getBacktestNav").mockResolvedValue(SAMPLE_NAV);

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);
    expect(useBacktestStore.getState().formErrors.start).toBe("bad start");

    await useBacktestStore.getState().submit(SAMPLE_REQUEST);
    const state = useBacktestStore.getState();
    expect(state.formErrors).toEqual({});
    expect(state.submitStatus).toBe("ok");
    expect(state.navSeries).toEqual(SAMPLE_NAV.nav_series);
  });

  it("fetchNav populates navSeries independently", async () => {
    vi.spyOn(backtestApi, "getBacktestNav").mockResolvedValue(SAMPLE_NAV);

    await useBacktestStore.getState().fetchNav(42);

    const state = useBacktestStore.getState();
    expect(state.navStatus).toBe("ok");
    expect(state.navSeries).toEqual(SAMPLE_NAV.nav_series);
    expect(state.navError).toBeNull();
  });

  it("fetchNav surfaces failures in navError without touching currentRun", async () => {
    vi.spyOn(backtestApi, "getBacktestNav").mockRejectedValue(new Error("404"));

    await useBacktestStore.getState().fetchNav(42);

    const state = useBacktestStore.getState();
    expect(state.navStatus).toBe("error");
    expect(state.navError).toBe("404");
    expect(state.currentRun).toBeNull();
  });

  it("reset returns to initial state", async () => {
    vi.spyOn(backtestApi, "runBacktest").mockResolvedValue(SAMPLE_RUN);
    vi.spyOn(backtestApi, "getBacktestNav").mockResolvedValue(SAMPLE_NAV);
    await useBacktestStore.getState().submit(SAMPLE_REQUEST);

    useBacktestStore.getState().reset();

    const state = useBacktestStore.getState();
    expect(state.submitStatus).toBe("idle");
    expect(state.navStatus).toBe("idle");
    expect(state.currentRun).toBeNull();
    expect(state.navSeries).toEqual([]);
    expect(state.formErrors).toEqual({});
    expect(state.submitError).toBeNull();
    expect(state.navError).toBeNull();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as backtestApi from "@/api/backtest";
import * as etfsApi from "@/api/etfs";
import { BacktestPage } from "@/pages/BacktestPage";
import { useBacktestStore } from "@/stores/backtest-store";
import { useEtfsStore } from "@/stores/etfs-store";

const SAMPLE_RUN: backtestApi.BacktestRun = {
  id: 9,
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

const SAMPLE_NAV: backtestApi.BacktestNavResponse = {
  id: 9,
  nav_series: [
    { date: "2025-01-01", nav: "100000" },
    { date: "2025-06-01", nav: "108000" },
    { date: "2025-12-01", nav: "112340" },
  ],
};

const SAMPLE_ETFS: etfsApi.EtfsApiResponse = {
  items: [
    { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
    { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
  ],
  total: 2,
  limit: 500,
  offset: 0,
};

describe("BacktestPage", () => {
  beforeEach(() => {
    useEtfsStore.getState().reset();
    useBacktestStore.getState().reset();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the empty placeholder initially", () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<BacktestPage />);
    expect(screen.getByTestId("result-empty")).toBeInTheDocument();
  });

  it("populates the ETF pool after the dictionary loads", async () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<BacktestPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-510300")).toBeInTheDocument();
      expect(screen.getByTestId("pool-510500")).toBeInTheDocument();
    });
  });

  it("renders the metrics cards and NAV chart after a successful submission", async () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    vi.spyOn(backtestApi, "runBacktest").mockResolvedValue(SAMPLE_RUN);
    vi.spyOn(backtestApi, "getBacktestNav").mockResolvedValue(SAMPLE_NAV);

    render(<BacktestPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-510300")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-510300"));
    fireEvent.change(screen.getByTestId("field-start"), { target: { value: "2025-01-01" } });
    fireEvent.change(screen.getByTestId("field-end"), { target: { value: "2025-12-31" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("result-success")).toBeInTheDocument();
    });
    expect(screen.getByTestId("metric-total_return")).toHaveTextContent("12.34%");
    expect(screen.getByTestId("metric-sharpe_ratio")).toHaveTextContent("1.200");
    expect(screen.getByTestId("nav-chart")).toBeInTheDocument();
  });

  it("shows a full-width error card when the submission fails with a network error", async () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    vi.spyOn(backtestApi, "runBacktest").mockRejectedValue(new Error("网络断开"));

    render(<BacktestPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-510300")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-510300"));
    fireEvent.change(screen.getByTestId("field-start"), { target: { value: "2025-01-01" } });
    fireEvent.change(screen.getByTestId("field-end"), { target: { value: "2025-12-31" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("result-error")).toBeInTheDocument();
      expect(screen.getByText("网络断开")).toBeInTheDocument();
    });
  });

  it("shows the ETF load failure inline in the form when the dictionary errors", async () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockRejectedValue(new Error("etfs 502"));

    render(<BacktestPage />);

    await waitFor(() => {
      expect(screen.getByText(/ETF 字典加载失败/)).toBeInTheDocument();
    });
    expect(screen.getByTestId("submit-button")).toBeDisabled();
  });
});

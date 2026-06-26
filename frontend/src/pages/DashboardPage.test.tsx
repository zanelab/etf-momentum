import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as etfsApi from "@/api/etfs";
import * as signalsApi from "@/api/signals";
import { DashboardPage } from "@/pages/DashboardPage";
import { useEtfsStore } from "@/stores/etfs-store";
import { useSignalsStore } from "@/stores/signals-store";

describe("DashboardPage", () => {
  beforeEach(() => {
    useSignalsStore.getState().reset();
    useEtfsStore.getState().reset();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the loading state initially", () => {
    render(<DashboardPage />);
    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });

  it("renders the empty state when the snapshot has zero rows", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals").mockResolvedValue({ date: null, rows: [] });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue({
      items: [],
      total: 0,
      limit: 500,
      offset: 0,
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "暂无信号快照" })).toBeInTheDocument();
    });
  });

  it("renders the error card when signals fetch fails", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals").mockRejectedValue(new Error("signals down"));
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue({
      items: [],
      total: 0,
      limit: 500,
      offset: 0,
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("信号加载失败")).toBeInTheDocument();
      expect(screen.getByText("signals down")).toBeInTheDocument();
    });
  });

  it("renders the ranking table with snapshot rows and joined ETF names", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals").mockResolvedValue({
      date: "2026-06-26",
      rows: [
        { etf_code: "510300", momentum_score: "0.123", rank: 1, action: "BUY" },
        { etf_code: "510500", momentum_score: null, rank: 2, action: "HOLD" },
      ],
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue({
      items: [
        { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
        { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
      ],
      total: 2,
      limit: 500,
      offset: 0,
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("沪深300ETF")).toBeInTheDocument();
      expect(screen.getByText("中证500ETF")).toBeInTheDocument();
    });
  });

  it("renders the warning banner and falls back to '—' when ETF dict fails", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals").mockResolvedValue({
      date: "2026-06-26",
      rows: [
        { etf_code: "510300", momentum_score: "0.5", rank: 1, action: "BUY" },
      ],
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockRejectedValue(new Error("etfs 502"));

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/ETF 字典加载失败/)).toBeInTheDocument();
    });
  });
});

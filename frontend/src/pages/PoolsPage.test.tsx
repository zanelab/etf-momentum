import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as etfsApi from "@/api/etfs";
import * as poolsApi from "@/api/pools";
import { PoolsPage } from "@/pages/PoolsPage";
import { useEtfsStore } from "@/stores/etfs-store";
import { usePoolsStore } from "@/stores/pools-store";

const SAMPLE_ETFS: etfsApi.EtfsApiResponse = {
  items: [
    { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
    { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
    { code: "510880", name: "红利ETF", market: "SH", category: "红利" },
  ],
  total: 3,
  limit: 500,
  offset: 0,
};

const SAMPLE_SUMMARY: poolsApi.EtfPoolSummary = {
  id: 1,
  name: "宽基核心",
  description: "沪深300+中证500",
  member_count: 2,
  created_at: "2026-06-27T00:00:00",
  updated_at: "2026-06-27T00:00:00",
};

const SAMPLE_DETAIL: poolsApi.EtfPoolDetail = {
  id: 1,
  name: "宽基核心",
  description: "沪深300+中证500",
  members: [
    { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基", position: 0 },
    { code: "510500", name: "中证500ETF", market: "SH", category: "宽基", position: 1 },
  ],
  created_at: "2026-06-27T00:00:00",
  updated_at: "2026-06-27T00:00:00",
};

describe("PoolsPage", () => {
  beforeEach(() => {
    usePoolsStore.getState().reset();
    useEtfsStore.getState().reset();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the loading state while pools are being fetched", () => {
    vi.spyOn(poolsApi, "listPools").mockImplementation(
      () => new Promise(() => {}),
    );
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<PoolsPage />);
    expect(screen.getByTestId("pools-loading")).toBeInTheDocument();
  });

  it("renders the empty-state list when no pools exist", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-empty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("pools-editor-empty")).toBeInTheDocument();
  });

  it("renders one card per pool", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({
      items: [SAMPLE_SUMMARY],
      total: 1,
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
    });
  });

  it("shows a retry button when the pools fetch fails", async () => {
    vi.spyOn(poolsApi, "listPools").mockRejectedValue(new Error("网络断开"));
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pools-error")).toBeInTheDocument();
    });
    expect(screen.getByText("网络断开")).toBeInTheDocument();
    expect(screen.getByTestId("pools-retry")).toBeInTheDocument();
  });

  it("enters create mode when '新建池' is clicked", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-empty")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pools-new"));

    await waitFor(() => {
      expect(screen.getByTestId("pool-editor-save")).toHaveTextContent("创建");
    });
    expect(screen.getByTestId("pool-editor-name")).toBeInTheDocument();
  });

  it("enters edit mode and prefills the form when a pool is clicked", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({
      items: [SAMPLE_SUMMARY],
      total: 1,
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    vi.spyOn(poolsApi, "getPool").mockResolvedValue(SAMPLE_DETAIL);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-list-card-1"));

    await waitFor(() => {
      expect(screen.getByTestId("pool-editor-name")).toHaveValue("宽基核心");
    });
    expect(screen.getByTestId("pool-editor-picker-510300")).toBeChecked();
    expect(screen.getByTestId("pool-editor-picker-510500")).toBeChecked();
  });

  it("creates a pool when the create form is submitted", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    const createSpy = vi.spyOn(poolsApi, "createPool").mockResolvedValue(SAMPLE_DETAIL);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-empty")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pools-new"));
    await waitFor(() => {
      expect(screen.getByTestId("pool-editor-name")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("pool-editor-name"), {
      target: { value: "宽基核心" },
    });
    fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
    fireEvent.click(screen.getByTestId("pool-editor-picker-510500"));
    fireEvent.click(screen.getByTestId("pool-editor-save"));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        name: "宽基核心",
        description: null,
        etf_codes: ["510300", "510500"],
      });
    });
  });

  it("shows a 409 error inline when the create form hits a duplicate name", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    vi.spyOn(poolsApi, "createPool").mockRejectedValue(
      new (await import("@/api/client")).ApiError(
        "Pool '宽基核心' already exists",
        409,
        "Pool '宽基核心' already exists",
      ),
    );
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-empty")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pools-new"));
    await waitFor(() => {
      expect(screen.getByTestId("pool-editor-name")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("pool-editor-name"), {
      target: { value: "宽基核心" },
    });
    fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
    fireEvent.click(screen.getByTestId("pool-editor-save"));

    await waitFor(() => {
      expect(screen.getByTestId("pool-editor-error-name")).toHaveTextContent(
        /already exists/,
      );
    });
  });

  it("asks for confirmation before deleting and removes the pool on confirm", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({
      items: [SAMPLE_SUMMARY],
      total: 1,
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    const deleteSpy = vi
      .spyOn(poolsApi, "deletePool")
      .mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-list-delete-1"));

    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith(1);
    });
    await waitFor(() => {
      expect(screen.queryByTestId("pool-list-card-1")).not.toBeInTheDocument();
    });
  });

  it("does not delete when the user cancels the confirmation", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({
      items: [SAMPLE_SUMMARY],
      total: 1,
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    const deleteSpy = vi.spyOn(poolsApi, "deletePool").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-list-delete-1"));

    expect(deleteSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
  });

  it("returns to the empty editor when cancel is pressed in edit mode", async () => {
    vi.spyOn(poolsApi, "listPools").mockResolvedValue({
      items: [SAMPLE_SUMMARY],
      total: 1,
    });
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(SAMPLE_ETFS);
    vi.spyOn(poolsApi, "getPool").mockResolvedValue(SAMPLE_DETAIL);
    render(<PoolsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-list-card-1"));
    await waitFor(() => {
      expect(screen.getByTestId("pool-editor-name")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("pool-editor-cancel"));

    await waitFor(() => {
      expect(screen.getByTestId("pools-editor-empty")).toBeInTheDocument();
    });
  });
});

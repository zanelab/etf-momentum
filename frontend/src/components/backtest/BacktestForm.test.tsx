import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EtfPoolSummary, EtfPoolDetail } from "@/api/pools";
import { BacktestForm } from "@/components/backtest/BacktestForm";

const SAMPLE_ETFS = [
  { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
  { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
  { code: "510880", name: "红利ETF", market: "SH", category: "红利" },
];

const SAMPLE_POOLS: EtfPoolSummary[] = [
  {
    id: 1,
    name: "宽基核心",
    description: "沪深300+中证500",
    member_count: 2,
    created_at: "2026-06-27T00:00:00",
    updated_at: "2026-06-27T00:00:00",
  },
];

const SAMPLE_POOL_DETAIL: EtfPoolDetail = {
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

const VALID_DATES = { start: "2025-01-01", end: "2025-12-31" };

function fillDates() {
  fireEvent.change(screen.getByTestId("field-start"), { target: { value: VALID_DATES.start } });
  fireEvent.change(screen.getByTestId("field-end"), { target: { value: VALID_DATES.end } });
}

describe("BacktestForm - custom mode (default)", () => {
  it("renders the ETF grid with one checkbox per ETF", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("backtest-picker-510300")).toBeInTheDocument();
    expect(screen.getByTestId("backtest-picker-510500")).toBeInTheDocument();
    expect(screen.getByTestId("backtest-picker-510880")).toBeInTheDocument();
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 0 / 3");
  });

  it("toggles an ETF selection and updates the count", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("backtest-picker-510300"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 1 / 3");

    fireEvent.click(screen.getByTestId("backtest-picker-510500"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 2 / 3");

    fireEvent.click(screen.getByTestId("backtest-picker-510300"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 1 / 3");
  });

  it("blocks submit when no ETF is selected", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={onSubmit}
      />,
    );
    fillDates();
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("error-etf_pool")).toHaveTextContent("请至少选择一只 ETF");
  });

  it("blocks submit when start >= end", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByTestId("backtest-picker-510300"));
    fireEvent.change(screen.getByTestId("field-start"), { target: { value: "2025-12-31" } });
    fireEvent.change(screen.getByTestId("field-end"), { target: { value: "2025-01-01" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("error-end")).toHaveTextContent("结束日期必须晚于起始日期");
  });

  it("submits a normalized BacktestRequest without pool_id in custom mode", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByTestId("backtest-picker-510300"));
    fireEvent.click(screen.getByTestId("backtest-picker-510500"));
    fillDates();
    fireEvent.change(screen.getByTestId("field-initial_cash"), { target: { value: "200000" } });
    fireEvent.change(screen.getByTestId("field-lookback"), { target: { value: "60" } });
    fireEvent.change(screen.getByTestId("field-top_n"), { target: { value: "3" } });
    fireEvent.change(screen.getByTestId("field-rebalance_freq"), { target: { value: "quarterly" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      etf_pool: ["510300", "510500"],
      pool_id: null,
      start: "2025-01-01",
      end: "2025-12-31",
      initial_cash: "200000",
      lookback: 60,
      skip: 21,
      top_n: 3,
      rebalance_freq: "quarterly",
    });
  });

  it("displays server-side field errors when present", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={vi.fn()}
        formErrors={{
          start: "start must be < end",
          etf_pool: "pool must not be empty",
        }}
      />,
    );
    expect(screen.getByTestId("error-etf_pool")).toHaveTextContent("pool must not be empty");
    expect(screen.getByTestId("error-start")).toHaveTextContent("start must be < end");
  });

  it("disables the form while a backtest submission is in flight", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={vi.fn()}
        disabled
      />,
    );
    expect(screen.getByTestId("submit-button")).toBeDisabled();
    expect(screen.getByTestId("backtest-picker-510300")).toBeDisabled();
    expect(screen.getByTestId("submit-button")).toHaveTextContent("回测中…");
  });

  it("disables submit when the ETF list failed to load", () => {
    render(
      <BacktestForm
        etfs={[]}
        etfsLoading={false}
        etfsError="500"
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("submit-button")).toBeDisabled();
    expect(screen.getByText(/ETF 字典加载失败/)).toBeInTheDocument();
  });
});

describe("BacktestForm - pool mode", () => {
  beforeEach(() => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("switches to pool mode and shows the pool dropdown", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));

    expect(screen.getByTestId("backtest-pool-mode-select")).toBeInTheDocument();
    expect(screen.getByTestId("backtest-pool-mode-select")).toHaveTextContent("宽基核心");
  });

  it("asks for confirmation before switching modes when a custom selection exists", () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("backtest-picker-510300"));
    fireEvent.click(screen.getByTestId("mode-pool"));

    expect(confirmSpy).toHaveBeenCalled();
    expect(screen.queryByTestId("backtest-pool-mode")).not.toBeInTheDocument();
  });

  it("does not confirm when switching to pool mode with an empty custom selection", () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("backtest-pool-mode")).toBeInTheDocument();
  });

  it("shows the link to /pools when the pool list is empty", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={[]}
        poolsLoading={false}
        poolsError={null}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    expect(screen.getByTestId("backtest-pool-mode-empty")).toBeInTheDocument();
    const link = screen.getByTestId("backtest-pool-mode-link");
    expect(link).toHaveAttribute("href", "/pools");
  });

  it("shows the retry button when the pool list failed to load", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={[]}
        poolsLoading={false}
        poolsError="网络断开"
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    expect(screen.getByTestId("backtest-pool-mode-error")).toHaveTextContent(
      "网络断开",
    );
    expect(screen.getByTestId("backtest-pool-mode-retry")).toBeInTheDocument();
  });

  it("auto-fills and locks the picker when a pool is selected", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        poolDetail={SAMPLE_POOL_DETAIL}
        poolDetailLoading={false}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    fireEvent.change(screen.getByTestId("backtest-pool-mode-select"), {
      target: { value: "1" },
    });

    expect(screen.getByTestId("backtest-pool-mode-picker-510300")).toBeChecked();
    expect(screen.getByTestId("backtest-pool-mode-picker-510500")).toBeChecked();
    expect(screen.getByTestId("backtest-pool-mode-picker-510300")).toBeDisabled();
    expect(screen.getByTestId("backtest-pool-mode-picker-locked-badge")).toBeInTheDocument();
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 2 / 3");
  });

  it("submits a request with pool_id and the pool's member codes", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        poolDetail={SAMPLE_POOL_DETAIL}
        poolDetailLoading={false}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    fireEvent.change(screen.getByTestId("backtest-pool-mode-select"), {
      target: { value: "1" },
    });
    fillDates();
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const call = onSubmit.mock.calls[0]?.[0];
    expect(call).toMatchObject({
      etf_pool: ["510300", "510500"],
      pool_id: 1,
      start: "2025-01-01",
      end: "2025-12-31",
    });
  });

  it("blocks submit in pool mode when no pool is selected", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    fillDates();
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("error-etf_pool")).toHaveTextContent("请至少选择一只 ETF");
  });

  it("switches back to custom mode and renders the picker (clean slate)", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        poolDetail={SAMPLE_POOL_DETAIL}
        poolDetailLoading={false}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("mode-pool"));
    fireEvent.change(screen.getByTestId("backtest-pool-mode-select"), {
      target: { value: "1" },
    });

    fireEvent.click(screen.getByTestId("mode-custom"));

    expect(screen.queryByTestId("backtest-pool-mode")).not.toBeInTheDocument();
    expect(screen.getByTestId("backtest-picker-510300")).toBeInTheDocument();
  });

  it("preserves a custom selection across a pool→custom round trip with no confirm", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        pools={SAMPLE_POOLS}
        poolsLoading={false}
        poolsError={null}
        poolDetail={SAMPLE_POOL_DETAIL}
        poolDetailLoading={false}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("backtest-picker-510300"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 1 / 3");

    fireEvent.click(screen.getByTestId("mode-pool"));
    fireEvent.click(screen.getByTestId("mode-custom"));

    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 1 / 3");
    expect(screen.getByTestId("backtest-picker-510300")).toBeChecked();
  });
});

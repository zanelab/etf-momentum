import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestForm } from "@/components/backtest/BacktestForm";

const SAMPLE_ETFS = [
  { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
  { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
  { code: "510880", name: "红利ETF", market: "SH", category: "红利" },
];

const VALID_DATES = { start: "2025-01-01", end: "2025-12-31" };

function fillDates() {
  fireEvent.change(screen.getByTestId("field-start"), { target: { value: VALID_DATES.start } });
  fireEvent.change(screen.getByTestId("field-end"), { target: { value: VALID_DATES.end } });
}

describe("BacktestForm", () => {
  it("renders the ETF pool grid with one checkbox per ETF", () => {
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("pool-510300")).toBeInTheDocument();
    expect(screen.getByTestId("pool-510500")).toBeInTheDocument();
    expect(screen.getByTestId("pool-510880")).toBeInTheDocument();
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
    fireEvent.click(screen.getByTestId("pool-510300"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 1 / 3");

    fireEvent.click(screen.getByTestId("pool-510500"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 2 / 3");

    fireEvent.click(screen.getByTestId("pool-510300"));
    expect(screen.getByTestId("pool-count")).toHaveTextContent("已选 1 / 3");
  });

  it("blocks submit when no ETF is selected and shows the error", () => {
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
    fireEvent.click(screen.getByTestId("pool-510300"));
    fireEvent.change(screen.getByTestId("field-start"), { target: { value: "2025-12-31" } });
    fireEvent.change(screen.getByTestId("field-end"), { target: { value: "2025-01-01" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("error-end")).toHaveTextContent("结束日期必须晚于起始日期");
  });

  it("blocks submit when lookback < 1", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByTestId("pool-510300"));
    fillDates();
    fireEvent.change(screen.getByTestId("field-lookback"), { target: { value: "0" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("error-lookback")).toHaveTextContent("回看天数必须 >= 1");
  });

  it("submits a normalized BacktestRequest when the form is valid", () => {
    const onSubmit = vi.fn();
    render(
      <BacktestForm
        etfs={SAMPLE_ETFS}
        etfsLoading={false}
        etfsError={null}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByTestId("pool-510300"));
    fireEvent.click(screen.getByTestId("pool-510500"));
    fillDates();
    fireEvent.change(screen.getByTestId("field-initial_cash"), { target: { value: "200000" } });
    fireEvent.change(screen.getByTestId("field-lookback"), { target: { value: "60" } });
    fireEvent.change(screen.getByTestId("field-top_n"), { target: { value: "3" } });
    fireEvent.change(screen.getByTestId("field-rebalance_freq"), { target: { value: "quarterly" } });
    fireEvent.click(screen.getByTestId("submit-button"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      etf_pool: ["510300", "510500"],
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
    expect(screen.getByTestId("pool-510300")).toBeDisabled();
    expect(screen.getByTestId("field-start")).toBeDisabled();
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

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricsCards } from "@/components/backtest/MetricsCards";

const FULL_METRICS = {
  total_return: "0.1234",
  annualized_return: "0.15",
  max_drawdown: "0.08",
  sharpe_ratio: "1.2",
  sortino_ratio: "1.5",
  calmar_ratio: "1.8",
};

describe("MetricsCards", () => {
  it("renders all six card labels", () => {
    render(<MetricsCards metrics={FULL_METRICS} />);
    expect(screen.getByText("总收益")).toBeInTheDocument();
    expect(screen.getByText("年化收益")).toBeInTheDocument();
    expect(screen.getByText("最大回撤")).toBeInTheDocument();
    expect(screen.getByText("夏普比率")).toBeInTheDocument();
    expect(screen.getByText("Sortino")).toBeInTheDocument();
    expect(screen.getByText("Calmar")).toBeInTheDocument();
  });

  it("formats percentage metrics with 2 decimals + %", () => {
    render(<MetricsCards metrics={FULL_METRICS} />);
    expect(screen.getByTestId("metric-total_return")).toHaveTextContent("12.34%");
    expect(screen.getByTestId("metric-annualized_return")).toHaveTextContent("15.00%");
    expect(screen.getByTestId("metric-max_drawdown")).toHaveTextContent("8.00%");
  });

  it("formats ratio metrics with 3 decimals", () => {
    render(<MetricsCards metrics={FULL_METRICS} />);
    expect(screen.getByTestId("metric-sharpe_ratio")).toHaveTextContent("1.200");
    expect(screen.getByTestId("metric-sortino_ratio")).toHaveTextContent("1.500");
    expect(screen.getByTestId("metric-calmar_ratio")).toHaveTextContent("1.800");
  });

  it("renders '—' for null metric values", () => {
    render(
      <MetricsCards
        metrics={{
          total_return: "0.1",
          annualized_return: null,
          max_drawdown: null,
          sharpe_ratio: null,
          sortino_ratio: null,
          calmar_ratio: null,
        }}
      />,
    );
    expect(screen.getByTestId("metric-total_return")).toHaveTextContent("10.00%");
    expect(screen.getByTestId("metric-annualized_return")).toHaveTextContent("—");
    expect(screen.getByTestId("metric-calmar_ratio")).toHaveTextContent("—");
  });

  it("renders all six cards as '—' when metrics is null", () => {
    render(<MetricsCards metrics={null} />);
    const placeholders = screen.getAllByText("—");
    expect(placeholders).toHaveLength(6);
  });

  it("accepts numeric values in addition to decimal strings", () => {
    render(
      <MetricsCards
        metrics={{
          total_return: 0.5,
          annualized_return: 0.25,
          max_drawdown: 0.1,
          sharpe_ratio: 2.345,
          sortino_ratio: 0,
          calmar_ratio: 0,
        }}
      />,
    );
    expect(screen.getByTestId("metric-total_return")).toHaveTextContent("50.00%");
    expect(screen.getByTestId("metric-sharpe_ratio")).toHaveTextContent("2.345");
  });
});

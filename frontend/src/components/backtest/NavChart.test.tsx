import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NavChart } from "@/components/backtest/NavChart";

const SAMPLE_DATA = [
  { date: "2025-01-01", nav: "100000" },
  { date: "2025-02-01", nav: "101500" },
  { date: "2025-03-01", nav: "103200" },
];

describe("NavChart", () => {
  it("renders a loading skeleton when loading=true", () => {
    render(<NavChart data={[]} loading />);
    expect(screen.getByTestId("nav-chart-loading")).toBeInTheDocument();
  });

  it("renders the empty-state card when there is no data and no error", () => {
    render(<NavChart data={[]} />);
    expect(screen.getByTestId("nav-chart-empty")).toBeInTheDocument();
  });

  it("renders an error card with the failure message", () => {
    render(<NavChart data={[]} errorMessage="404 not found" />);
    const card = screen.getByTestId("nav-chart-error");
    expect(card).toBeInTheDocument();
    expect(card).toHaveTextContent("NAV 数据加载失败");
    expect(card).toHaveTextContent("404 not found");
  });

  it("renders the chart wrapper when data is present", () => {
    const { container } = render(<NavChart data={SAMPLE_DATA} width={500} height={300} />);
    expect(screen.getByTestId("nav-chart")).toBeInTheDocument();
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBeGreaterThan(0);
  });
});

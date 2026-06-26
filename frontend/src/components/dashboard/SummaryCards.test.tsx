import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SummaryCards } from "@/components/dashboard/SummaryCards";

describe("SummaryCards", () => {
  const baseProps = {
    date: "2026-06-26",
    total: 12,
    counts: { BUY: 3, HOLD: 5, WATCH: 4 },
  };

  it("renders the snapshot date verbatim when provided", () => {
    render(<SummaryCards {...baseProps} />);
    expect(screen.getByText("2026-06-26")).toBeInTheDocument();
  });

  it("renders '—' when snapshot date is null", () => {
    render(<SummaryCards {...baseProps} date={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders the total ETF count", () => {
    render(<SummaryCards {...baseProps} />);
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders per-action counts", () => {
    render(<SummaryCards {...baseProps} />);
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders all five card labels", () => {
    render(<SummaryCards {...baseProps} />);
    expect(screen.getByText("Snapshot 日期")).toBeInTheDocument();
    expect(screen.getByText("ETF 总数")).toBeInTheDocument();
    expect(screen.getByText("BUY")).toBeInTheDocument();
    expect(screen.getByText("HOLD")).toBeInTheDocument();
    expect(screen.getByText("WATCH")).toBeInTheDocument();
  });
});

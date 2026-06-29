import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RowProgressBar } from "../RowProgressBar";
import type { ProgressInfo } from "@/api/hooks";

const sample: ProgressInfo = {
  code: "510300",
  from_date: "2024-04-19",
  to_date: "2024-04-21",
  current_date: "2024-04-20",
  total_days: 3,
  completed_days: 2,
  overall_index: 2,
  overall_total: 3,
  started_at: "2026-06-29T10:00:00Z",
};

describe("RowProgressBar", () => {
  it("renders a progressbar with the computed percentage", () => {
    render(<RowProgressBar info={sample} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toBeInTheDocument();
    // completed_days=2 / total_days=3 ≈ 67%
    expect(bar.getAttribute("aria-valuenow")).toBe("67");
  });

  it("displays current date and total days", () => {
    render(<RowProgressBar info={sample} />);
    expect(screen.getByText(/2024-04-20/)).toBeInTheDocument();
    expect(screen.getByText(/3.*天/)).toBeInTheDocument();
  });
});
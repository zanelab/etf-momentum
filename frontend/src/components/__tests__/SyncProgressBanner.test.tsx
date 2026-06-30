import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SyncProgressBanner } from "../SyncProgressBanner";
import type { ProgressInfo } from "@/api/hooks";

const sampleProgress: ProgressInfo[] = [
  {
    code: "510300",
    from_date: "2024-04-19",
    to_date: "2024-04-21",
    current_date: "2024-04-20",
    total_days: 3,
    completed_days: 2,
    overall_index: 2,
    overall_total: 3,
    started_at: "2026-06-29T10:00:00Z",
  },
];

describe("SyncProgressBanner", () => {
  it("returns null when progress is empty", () => {
    const { container } = render(<SyncProgressBanner progress={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows total progress and current code/day", () => {
    render(<SyncProgressBanner progress={sampleProgress} />);
    expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
    expect(screen.getByText(/510300/)).toBeInTheDocument();
    expect(screen.getByText(/2024-04-20/)).toBeInTheDocument();
  });

  it("aggregates overall_index across multiple codes", () => {
    const two: ProgressInfo[] = [
      { ...sampleProgress[0], code: "510300", overall_index: 5, overall_total: 10 },
      { ...sampleProgress[0], code: "510500", overall_index: 6, overall_total: 10 },
    ];
    render(<SyncProgressBanner progress={two} />);
    // overall_index should reflect the max (most advanced)
    expect(screen.getByText(/6 \/ 10/)).toBeInTheDocument();
    // current should be the most advanced code
    expect(screen.getByText(/510500/)).toBeInTheDocument();
  });

  it("renders red cancelled style when isCancelled=true", () => {
    const { container } = render(<SyncProgressBanner progress={sampleProgress} isCancelled={true} />);
    expect(container.firstChild).toHaveClass("bg-red-50");
    expect(screen.getByText(/已取消/)).toBeInTheDocument();
  });

  it("renders blue progress style when isCancelled=false", () => {
    const { container } = render(<SyncProgressBanner progress={sampleProgress} isCancelled={false} />);
    expect(container.firstChild).toHaveClass("bg-blue-50");
    expect(screen.getByText(/同步进行中/)).toBeInTheDocument();
  });
});
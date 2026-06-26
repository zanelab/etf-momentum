import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "@/components/dashboard/EmptyState";

describe("EmptyState", () => {
  it("renders the empty-state heading", () => {
    render(<EmptyState />);
    expect(
      screen.getByRole("heading", { name: "暂无信号快照" }),
    ).toBeInTheDocument();
  });

  it("shows the CLI command for computing the latest snapshot", () => {
    render(<EmptyState />);
    expect(
      screen.getByText("python -m app.signals.compute_latest"),
    ).toBeInTheDocument();
  });
});

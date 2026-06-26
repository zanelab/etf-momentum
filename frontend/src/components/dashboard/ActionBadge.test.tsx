import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActionBadge } from "@/components/dashboard/ActionBadge";

describe("ActionBadge", () => {
  it("renders the action text verbatim", () => {
    render(<ActionBadge action="BUY" />);
    expect(screen.getByText("BUY")).toBeInTheDocument();
  });

  it("applies the green tone for BUY", () => {
    render(<ActionBadge action="BUY" />);
    const badge = screen.getByText("BUY");
    expect(badge.className).toMatch(/emerald/);
  });

  it("applies the blue tone for HOLD", () => {
    render(<ActionBadge action="HOLD" />);
    const badge = screen.getByText("HOLD");
    expect(badge.className).toMatch(/sky/);
  });

  it("applies the gray tone for WATCH", () => {
    render(<ActionBadge action="WATCH" />);
    const badge = screen.getByText("WATCH");
    expect(badge.className).toMatch(/slate/);
  });

  it("falls back to gray and shows raw text for unknown actions", () => {
    render(<ActionBadge action="HOLD_AND_MODIFY" />);
    const badge = screen.getByText("HOLD_AND_MODIFY");
    expect(badge.className).toMatch(/slate/);
  });
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/AppShell";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell>
        <p>page body</p>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("renders the four top-nav entries", () => {
    renderAt("/");
    expect(screen.getByText("仪表盘")).toBeInTheDocument();
    expect(screen.getByText("持仓")).toBeInTheDocument();
    expect(screen.getByText("今日调仓")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });

  it("renders children in the main area", () => {
    renderAt("/");
    expect(screen.getByText("page body")).toBeInTheDocument();
  });

  it("links the top-nav entries to the right paths", () => {
    renderAt("/");
    const dashboardLink = screen.getByRole("link", { name: "仪表盘" });
    const portfolioLink = screen.getByRole("link", { name: "持仓" });
    const signalsLink = screen.getByRole("link", { name: "今日调仓" });
    expect(dashboardLink).toHaveAttribute("href", "/");
    expect(portfolioLink).toHaveAttribute("href", "/portfolio");
    expect(signalsLink).toHaveAttribute("href", "/signals");
  });

  it("renders the brand heading", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: "ETF Momentum" })).toBeInTheDocument();
  });

  it("calls onSettingsClick when the settings trigger is clicked", async () => {
    const user = (await import("@testing-library/user-event")).default;
    const onClick = vi.fn();
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppShell onSettingsClick={onClick}>
          <p>x</p>
        </AppShell>
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: "设置" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

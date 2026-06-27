import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { Layout } from "@/layouts/Layout";

function renderLayout(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<div data-testid="child">dashboard</div>} />
          <Route path="/pools" element={<div data-testid="child">pools</div>} />
          <Route path="/backtest" element={<div data-testid="child">backtest</div>} />
          <Route path="/health" element={<div data-testid="child">health</div>} />
          <Route path="*" element={<div data-testid="child">other</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  it("renders the four nav-link labels", () => {
    renderLayout("/dashboard");
    expect(screen.getByText("动量看板")).toBeInTheDocument();
    expect(screen.getByText("策略池")).toBeInTheDocument();
    expect(screen.getByText("回测")).toBeInTheDocument();
    expect(screen.getByText("健康检查")).toBeInTheDocument();
  });

  it("renders the page title in the header", () => {
    renderLayout("/dashboard");
    expect(
      screen.getByRole("heading", { name: "A 股 ETF 动量策略系统" }),
    ).toBeInTheDocument();
  });

  it("marks the matching NavLink with aria-current='page'", () => {
    renderLayout("/pools");
    const poolsLink = screen.getByRole("link", { name: "策略池" });
    expect(poolsLink.getAttribute("aria-current")).toBe("page");
  });

  it("does NOT mark non-matching links as current", () => {
    renderLayout("/pools");
    const dashboardLink = screen.getByRole("link", { name: "动量看板" });
    const backtestLink = screen.getByRole("link", { name: "回测" });
    const healthLink = screen.getByRole("link", { name: "健康检查" });
    expect(dashboardLink.getAttribute("aria-current")).toBeNull();
    expect(backtestLink.getAttribute("aria-current")).toBeNull();
    expect(healthLink.getAttribute("aria-current")).toBeNull();
  });

  it("marks a different link as active when the pathname changes", () => {
    renderLayout("/backtest");
    const backtestLink = screen.getByRole("link", { name: "回测" });
    expect(backtestLink.getAttribute("aria-current")).toBe("page");
  });

  it("renders the child route via <Outlet />", () => {
    renderLayout("/pools");
    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByTestId("child").textContent).toBe("pools");
  });
});
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Sidebar } from "@/components/Sidebar";

function renderSidebar(props: { open: boolean; onClose: () => void }) {
  return render(
    <MemoryRouter>
      <Sidebar {...props} />
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("renders 6 settings entries when open", () => {
    renderSidebar({ open: true, onClose: () => {} });
    expect(screen.getByText("静态池")).toBeInTheDocument();
    expect(screen.getByText("主题词典")).toBeInTheDocument();
    expect(screen.getByText("策略参数")).toBeInTheDocument();
    expect(screen.getByText("动态池")).toBeInTheDocument();
    expect(screen.getByText("回测")).toBeInTheDocument();
    expect(screen.getByText("数据源")).toBeInTheDocument();
  });

  it("does not render entries when closed", () => {
    renderSidebar({ open: false, onClose: () => {} });
    expect(screen.queryByText("静态池")).not.toBeInTheDocument();
  });

  it("navigates each entry to the right path", () => {
    renderSidebar({ open: true, onClose: () => {} });
    expect(screen.getByRole("link", { name: "静态池" })).toHaveAttribute("href", "/pool");
    expect(screen.getByRole("link", { name: "动态池" })).toHaveAttribute("href", "/dynamic-pool");
    expect(screen.getByRole("link", { name: "数据源" })).toHaveAttribute("href", "/datasource");
  });

  it("calls onClose when an entry is clicked", async () => {
    const onClose = vi.fn();
    renderSidebar({ open: true, onClose });
    await userEvent.click(screen.getByRole("link", { name: "静态池" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", async () => {
    const onClose = vi.fn();
    renderSidebar({ open: true, onClose });
    await userEvent.click(screen.getByTestId("sidebar-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape is pressed", async () => {
    const onClose = vi.fn();
    renderSidebar({ open: true, onClose });
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
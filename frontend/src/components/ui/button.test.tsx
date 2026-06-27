import { createRef } from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders a default button with default variant + size classes", () => {
    render(<Button>提交</Button>);
    const btn = screen.getByRole("button", { name: "提交" });
    expect(btn).toBeInTheDocument();
    // default variant adds bg-primary; default size adds h-10
    expect(btn.className).toMatch(/bg-primary/);
    expect(btn.className).toMatch(/h-10/);
  });

  it("applies destructive variant classes when variant='destructive'", () => {
    render(<Button variant="destructive">删除</Button>);
    const btn = screen.getByRole("button", { name: "删除" });
    expect(btn.className).toMatch(/bg-destructive/);
  });

  it("applies outline variant classes when variant='outline'", () => {
    render(<Button variant="outline">取消</Button>);
    const btn = screen.getByRole("button", { name: "取消" });
    expect(btn.className).toMatch(/border/);
    expect(btn.className).toMatch(/bg-background/);
  });

  it("applies size='sm' classes (h-9 px-3)", () => {
    render(<Button size="sm">小</Button>);
    const btn = screen.getByRole("button", { name: "小" });
    expect(btn.className).toMatch(/h-9/);
  });

  it("applies size='icon' classes (h-10 w-10)", () => {
    render(<Button size="icon" aria-label="图标">★</Button>);
    const btn = screen.getByRole("button", { name: "图标" });
    expect(btn.className).toMatch(/h-10/);
    expect(btn.className).toMatch(/w-10/);
  });

  it("merges a passed className into the button class", () => {
    render(<Button className="custom-class">合并</Button>);
    const btn = screen.getByRole("button", { name: "合并" });
    expect(btn.className).toMatch(/custom-class/);
    expect(btn.className).toMatch(/bg-primary/);
  });

  it("invokes onClick exactly once when enabled", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>点我</Button>);
    fireEvent.click(screen.getByRole("button", { name: "点我" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not invoke onClick when disabled", () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        禁用
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: "禁用" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("forwards refs to the underlying button element", () => {
    const ref = createRef<HTMLButtonElement>();
    render(<Button ref={ref}>ref 测试</Button>);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    expect(ref.current?.textContent).toBe("ref 测试");
  });
});
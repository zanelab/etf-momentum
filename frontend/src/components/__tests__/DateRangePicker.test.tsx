import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DateRangePicker } from "../DateRangePicker";

function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

describe("DateRangePicker", () => {
  it("does not render when open=false", () => {
    render(<DateRangePicker open={false} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders with default from=today-30, to=today", () => {
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} />);
    const fromInput = screen.getByLabelText(/from/i) as HTMLInputElement;
    const toInput = screen.getByLabelText(/to/i) as HTMLInputElement;
    expect(fromInput.value).toBe(todayISO(-30));
    expect(toInput.value).toBe(todayISO(0));
  });

  it("confirm button disabled when from > to", async () => {
    const user = userEvent.setup();
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} />);
    const fromInput = screen.getByLabelText(/from/i);
    await user.clear(fromInput);
    await user.type(fromInput, todayISO(10));
    const confirmBtn = screen.getByRole("button", { name: /开始同步/ });
    expect(confirmBtn).toBeDisabled();
    expect(screen.getByText(/from_date 必须早于/i)).toBeInTheDocument();
  });

  it("calls onConfirm with { from_date, to_date } when valid", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={onConfirm} isSubmitting={false} />);
    const fromInput = screen.getByLabelText(/from/i);
    const toInput = screen.getByLabelText(/to/i);
    await user.clear(fromInput);
    await user.type(fromInput, "2024-04-19");
    await user.clear(toInput);
    await user.type(toInput, "2024-04-21");
    await user.click(screen.getByRole("button", { name: /开始同步/ }));
    expect(onConfirm).toHaveBeenCalledWith({ from_date: "2024-04-19", to_date: "2024-04-21" });
  });

  it("shows backend error message when provided", () => {
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} errorMessage="同步失败" />);
    expect(screen.getByText(/同步失败/)).toBeInTheDocument();
  });

  it("confirm button disabled while isSubmitting", () => {
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={true} />);
    expect(screen.getByRole("button", { name: /同步中|开始同步/ })).toBeDisabled();
  });

  it("cancel button calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<DateRangePicker open={true} onClose={onClose} onConfirm={() => {}} isSubmitting={false} />);
    await user.click(screen.getByRole("button", { name: /取消/ }));
    expect(onClose).toHaveBeenCalled();
  });
});
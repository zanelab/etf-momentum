import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EtfPickerGrid } from "@/components/pools/EtfPickerGrid";

const SAMPLE_ETFS = [
  { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
  { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
  { code: "510880", name: "红利ETF", market: "SH", category: "红利" },
];

function makeEtfs(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    code: `${(i + 100).toString().padStart(6, "0")}`,
    name: `测试ETF${i + 1}`,
    market: "SH" as const,
    category: "宽基" as const,
  }));
}

describe("EtfPickerGrid", () => {
  it("renders one checkbox per ETF and the selection count", () => {
    render(
      <EtfPickerGrid
        etfs={SAMPLE_ETFS}
        selected={[]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("etf-picker-510300")).toBeInTheDocument();
    expect(screen.getByTestId("etf-picker-510500")).toBeInTheDocument();
    expect(screen.getByTestId("etf-picker-510880")).toBeInTheDocument();
    expect(screen.getByTestId("etf-picker-count")).toHaveTextContent(
      "已选 0 / 3",
    );
  });

  it("toggles an ETF and reports the new selection", () => {
    const onChange = vi.fn();
    render(
      <EtfPickerGrid
        etfs={SAMPLE_ETFS}
        selected={["510300"]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("etf-picker-510500"));
    expect(onChange).toHaveBeenCalledWith(["510300", "510500"]);
  });

  it("removes a selected ETF when toggled again", () => {
    const onChange = vi.fn();
    render(
      <EtfPickerGrid
        etfs={SAMPLE_ETFS}
        selected={["510300", "510500"]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("etf-picker-510300"));
    expect(onChange).toHaveBeenCalledWith(["510500"]);
  });

  it("filters ETFs by code, name, or category via the search input", () => {
    render(
      <EtfPickerGrid
        etfs={SAMPLE_ETFS}
        selected={[]}
        onChange={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByTestId("etf-picker-search"), {
      target: { value: "红利" },
    });
    expect(screen.getByTestId("etf-picker-510880")).toBeInTheDocument();
    expect(screen.queryByTestId("etf-picker-510300")).not.toBeInTheDocument();
  });

  it("shows only the first 12 by default and reveals the rest via the show-more button", () => {
    const many = makeEtfs(20);
    render(
      <EtfPickerGrid
        etfs={many}
        selected={[]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("etf-picker-000100")).toBeInTheDocument();
    expect(screen.queryByTestId("etf-picker-000119")).not.toBeInTheDocument();
    const button = screen.getByTestId("etf-picker-show-more");
    expect(button).toHaveTextContent("显示剩余 8 只");

    fireEvent.click(button);
    expect(screen.getByTestId("etf-picker-000119")).toBeInTheDocument();
  });

  it("disables all checkboxes and skips onChange when locked=true", () => {
    const onChange = vi.fn();
    render(
      <EtfPickerGrid
        etfs={SAMPLE_ETFS}
        selected={["510300"]}
        onChange={onChange}
        locked
      />,
    );
    expect(screen.getByTestId("etf-picker-locked-badge")).toBeInTheDocument();
    expect(screen.getByTestId("etf-picker-510300")).toBeChecked();
    expect(screen.getByTestId("etf-picker-510300")).toBeDisabled();

    fireEvent.click(screen.getByTestId("etf-picker-510500"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("renders loading state when loading=true", () => {
    render(
      <EtfPickerGrid
        etfs={[]}
        selected={[]}
        onChange={vi.fn()}
        loading
      />,
    );
    expect(screen.getByTestId("etf-picker-loading")).toBeInTheDocument();
  });

  it("renders error state when error is set", () => {
    render(
      <EtfPickerGrid
        etfs={[]}
        selected={[]}
        onChange={vi.fn()}
        error="500"
      />,
    );
    expect(screen.getByTestId("etf-picker-error")).toHaveTextContent("500");
  });

  it("renders empty state when etfs is empty", () => {
    render(
      <EtfPickerGrid
        etfs={[]}
        selected={[]}
        onChange={vi.fn()}
        emptyMessage="字典为空"
      />,
    );
    expect(screen.getByTestId("etf-picker-empty")).toHaveTextContent("字典为空");
  });

  it("renders no-match state when search filters everything out", () => {
    render(
      <EtfPickerGrid
        etfs={SAMPLE_ETFS}
        selected={[]}
        onChange={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByTestId("etf-picker-search"), {
      target: { value: "ZZZZ" },
    });
    expect(screen.getByTestId("etf-picker-no-match")).toBeInTheDocument();
  });
});

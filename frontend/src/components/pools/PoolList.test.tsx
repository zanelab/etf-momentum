import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EtfPoolSummary } from "@/api/pools";
import { PoolList } from "@/components/pools/PoolList";

const SAMPLE_POOLS: EtfPoolSummary[] = [
  {
    id: 1,
    name: "宽基核心",
    description: "沪深300+中证500",
    member_count: 2,
    created_at: "2026-06-27T00:00:00",
    updated_at: "2026-06-27T00:00:00",
  },
  {
    id: 2,
    name: "红利精选",
    description: null,
    member_count: 5,
    created_at: "2026-06-27T00:00:00",
    updated_at: "2026-06-27T00:00:00",
  },
];

describe("PoolList", () => {
  it("renders the empty state when no pools are provided", () => {
    render(
      <PoolList pools={[]} onSelect={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByTestId("pool-list-empty")).toBeInTheDocument();
    expect(screen.getByTestId("pool-list-empty")).toHaveTextContent("暂无策略池");
  });

  it("renders one card per pool with name, description, and count", () => {
    render(
      <PoolList pools={SAMPLE_POOLS} onSelect={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByTestId("pool-list-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("pool-list-card-2")).toBeInTheDocument();
    expect(screen.getByTestId("pool-list-count-1")).toHaveTextContent("2 只");
    expect(screen.getByTestId("pool-list-count-2")).toHaveTextContent("5 只");
  });

  it("triggers onSelect when a card is clicked", () => {
    const onSelect = vi.fn();
    render(
      <PoolList pools={SAMPLE_POOLS} onSelect={onSelect} onDelete={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId("pool-list-card-1"));
    expect(onSelect).toHaveBeenCalledWith(SAMPLE_POOLS[0]);
  });

  it("triggers onDelete when the delete button is clicked without bubbling to onSelect", () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    render(
      <PoolList
        pools={SAMPLE_POOLS}
        onSelect={onSelect}
        onDelete={onDelete}
      />,
    );
    fireEvent.click(screen.getByTestId("pool-list-delete-2"));
    expect(onDelete).toHaveBeenCalledWith(SAMPLE_POOLS[1]);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("applies the selected style to the matching pool", () => {
    render(
      <PoolList
        pools={SAMPLE_POOLS}
        selectedId={2}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByTestId("pool-list-card-2").className).toContain(
      "border-primary",
    );
    expect(screen.getByTestId("pool-list-card-1").className).not.toContain(
      "ring-1",
    );
  });
});

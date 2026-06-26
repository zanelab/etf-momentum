import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SignalRankingTable } from "@/components/dashboard/SignalRankingTable";
import type { EtfItem } from "@/api/etfs";
import type { SignalRow } from "@/api/signals";

const ETF_DICT: Map<string, EtfItem> = new Map([
  ["510300", { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" }],
  ["510500", { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" }],
  ["512760", { code: "512760", name: "半导体ETF", market: "SH", category: "行业" }],
]);

function row(partial: Partial<SignalRow>): SignalRow {
  return {
    etf_code: "510300",
    momentum_score: "0.1234",
    rank: 1,
    action: "BUY",
    ...partial,
  };
}

describe("SignalRankingTable", () => {
  it("renders the BUY section with the count of BUY rows", () => {
    const rows: SignalRow[] = [
      row({ etf_code: "510300", action: "BUY", rank: 1 }),
      row({ etf_code: "510500", action: "BUY", rank: 2 }),
      row({ etf_code: "512760", action: "HOLD", rank: 3 }),
    ];
    render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    expect(screen.getByText(/建议买入（BUY） · 2/)).toBeInTheDocument();
  });

  it("renders the 其它 section with the count of non-BUY rows", () => {
    const rows: SignalRow[] = [
      row({ etf_code: "510300", action: "BUY", rank: 1 }),
      row({ etf_code: "510500", action: "HOLD", rank: 2 }),
      row({ etf_code: "512760", action: "WATCH", rank: 3 }),
    ];
    render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    expect(screen.getByText(/其它（HOLD \/ WATCH） · 2/)).toBeInTheDocument();
  });

  it("omits the 其它 section when there are no non-BUY rows", () => {
    const rows: SignalRow[] = [row({ etf_code: "510300", action: "BUY", rank: 1 })];
    render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    expect(screen.queryByText(/其它/)).toBeNull();
  });

  it("shows '—' for name and category when ETF is not in the dict", () => {
    const rows: SignalRow[] = [row({ etf_code: "999999", action: "BUY", rank: 1 })];
    const { container } = render(<SignalRankingTable rows={rows} etfDict={new Map()} />);
    const table = container.querySelector("table")!;
    const cells = within(table).getAllByText("—");
    expect(cells.length).toBeGreaterThanOrEqual(2);
  });

  it("formats momentum_score to 4 significant digits", () => {
    const rows: SignalRow[] = [row({ etf_code: "510300", momentum_score: "0.123456" })];
    render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    expect(screen.getByText("0.1235")).toBeInTheDocument();
  });

  it("renders '—' for null momentum_score", () => {
    const rows: SignalRow[] = [row({ etf_code: "510300", momentum_score: null })];
    render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("sorts BUY rows by rank ascending", () => {
    const rows: SignalRow[] = [
      row({ etf_code: "510500", action: "BUY", rank: 2 }),
      row({ etf_code: "510300", action: "BUY", rank: 1 }),
    ];
    const { container } = render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    const buyRows = container.querySelectorAll("tbody tr");
    expect(buyRows[0]?.textContent).toMatch(/510300/);
    expect(buyRows[1]?.textContent).toMatch(/510500/);
  });

  it("renders the empty-BUY placeholder when no rows are BUY", () => {
    const rows: SignalRow[] = [row({ etf_code: "510300", action: "HOLD", rank: 1 })];
    render(<SignalRankingTable rows={rows} etfDict={ETF_DICT} />);
    expect(screen.getByText("当前无 BUY 建议")).toBeInTheDocument();
  });
});

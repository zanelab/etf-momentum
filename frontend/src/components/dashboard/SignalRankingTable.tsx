import { ActionBadge } from "@/components/dashboard/ActionBadge";
import type { EtfItem } from "@/api/etfs";
import type { SignalRow } from "@/api/signals";

export interface SignalRankingTableProps {
  rows: SignalRow[];
  etfDict: Map<string, EtfItem>;
}

function formatScore(score: string | null): string {
  if (score === null) return "—";
  const n = Number.parseFloat(score);
  if (Number.isNaN(n)) return "—";
  return n.toPrecision(4);
}

function compareRows(a: SignalRow, b: SignalRow): number {
  const aRank = a.rank ?? Number.POSITIVE_INFINITY;
  const bRank = b.rank ?? Number.POSITIVE_INFINITY;
  if (aRank !== bRank) return aRank - bRank;
  return a.etf_code.localeCompare(b.etf_code);
}

function splitSections(rows: SignalRow[]): { buys: SignalRow[]; others: SignalRow[] } {
  const buys = rows.filter((r) => r.action === "BUY").sort(compareRows);
  const others = rows.filter((r) => r.action !== "BUY").sort(compareRows);
  return { buys, others };
}

function TableBody({ rows, etfDict }: { rows: SignalRow[]; etfDict: Map<string, EtfItem> }) {
  return (
    <tbody>
      {rows.map((row) => {
        const etf = etfDict.get(row.etf_code);
        return (
          <tr key={row.etf_code} className="border-t">
            <td className="px-3 py-2 text-sm text-muted-foreground">{row.rank ?? "—"}</td>
            <td className="px-3 py-2 text-sm font-mono">{row.etf_code}</td>
            <td className="px-3 py-2 text-sm">{etf?.name ?? "—"}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground">{etf?.category ?? "—"}</td>
            <td className="px-3 py-2 text-sm font-mono">{formatScore(row.momentum_score)}</td>
            <td className="px-3 py-2">
              <ActionBadge action={row.action} />
            </td>
          </tr>
        );
      })}
    </tbody>
  );
}

export function SignalRankingTable({ rows, etfDict }: SignalRankingTableProps) {
  const { buys, others } = splitSections(rows);

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-sm font-medium text-muted-foreground">
          建议买入（BUY） · {buys.length}
        </h3>
        {buys.length === 0 ? (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            当前无 BUY 建议
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-left">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Rank</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Code</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Name</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Category</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Score</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Action</th>
                </tr>
              </thead>
              <TableBody rows={buys} etfDict={etfDict} />
            </table>
          </div>
        )}
      </section>

      {others.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            其它（HOLD / WATCH） · {others.length}
          </h3>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-left">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Rank</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Code</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Name</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Category</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Score</th>
                  <th className="px-3 py-2 text-xs font-medium uppercase">Action</th>
                </tr>
              </thead>
              <TableBody rows={others} etfDict={etfDict} />
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

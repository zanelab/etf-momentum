// Portfolio overview table + totals. Polls every 5s.
import { usePortfolio } from "@/api/hooks";

const fmt = (n: number) =>
  n.toLocaleString(undefined, { maximumFractionDigits: 2 });

export default function Portfolio() {
  const portfolio = usePortfolio();
  if (portfolio.isLoading) return <p>加载中…</p>;
  if (portfolio.error) return <p className="text-red-600">加载失败</p>;
  const data = portfolio.data;
  if (!data) return null;

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-lg font-semibold">当前持仓 · {data.as_of}</h2>
      </header>
      <div className="grid grid-cols-3 gap-4">
        <Stat label="总市值" value={`¥${fmt(data.total_market_value)}`} />
        <Stat label="总成本" value={`¥${fmt(data.total_cost)}`} />
        <Stat
          label="总盈亏"
          value={`¥${fmt(data.total_pnl)}`}
          tone={data.total_pnl >= 0 ? "pos" : "neg"}
        />
      </div>
      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-right">股数</th>
              <th className="px-3 py-2 text-right">成本</th>
              <th className="px-3 py-2 text-right">现价</th>
              <th className="px-3 py-2 text-right">市值</th>
              <th className="px-3 py-2 text-right">盈亏</th>
            </tr>
          </thead>
          <tbody>
            {data.holdings.map((h) => (
              <tr key={h.code} className="border-t">
                <td className="px-3 py-1.5 font-mono">{h.code}</td>
                <td className="px-3 py-1.5 text-right">{h.shares.toLocaleString()}</td>
                <td className="px-3 py-1.5 text-right">{fmt(h.cost_price)}</td>
                <td className="px-3 py-1.5 text-right">{fmt(h.current_price)}</td>
                <td className="px-3 py-1.5 text-right">{fmt(h.market_value)}</td>
                <td
                  className={`px-3 py-1.5 text-right ${
                    h.pnl >= 0 ? "text-emerald-700" : "text-rose-700"
                  }`}
                >
                  {fmt(h.pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg";
}) {
  return (
    <div className="rounded border p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold ${
          tone === "pos" ? "text-emerald-700" : tone === "neg" ? "text-rose-700" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}

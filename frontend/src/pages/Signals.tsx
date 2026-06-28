// Today's buy/sell signal cards. Polls every 5s.
import { useSignalsToday } from "@/api/hooks";

export default function Signals() {
  const signals = useSignalsToday();
  if (signals.isLoading) return <p>加载中…</p>;
  if (signals.error) return <p className="text-red-600">加载失败</p>;
  const data = signals.data;
  if (!data) return null;

  const sells = data.signals.filter((s) => s.type === "SELL");
  const buys = data.signals.filter((s) => s.type === "BUY");

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">调仓信号 · {data.as_of}</h2>
      </header>
      <SignalGroup title="卖出" entries={sells} tone="sell" />
      <SignalGroup title="买入" entries={buys} tone="buy" />
    </section>
  );
}

function SignalGroup({
  title,
  entries,
  tone,
}: {
  title: string;
  entries: ReturnType<typeof useSignalsToday>["data"] extends infer T
    ? T extends { signals: infer S }
      ? S
      : never
    : never;
  tone: "buy" | "sell";
}) {
  const accent =
    tone === "buy"
      ? "border-emerald-300 bg-emerald-50"
      : "border-rose-300 bg-rose-50";
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-muted-foreground">
        {title}（{entries.length}）
      </h3>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">无</p>
        ) : (
          entries.map((s, i) => (
            <div key={`${s.etf}-${i}`} className={`rounded border ${accent} p-3`}>
              <div className="flex items-baseline justify-between">
                <span className="font-mono font-medium">{s.etf}</span>
                <span className="text-xs text-muted-foreground">{s.type}</span>
              </div>
              <p className="mt-1 text-sm">{s.reason}</p>
              {s.shares != null && (
                <p className="mt-1 text-xs text-muted-foreground">
                  数量：{s.shares.toLocaleString()} 股
                </p>
              )}
              {s.target_value != null && (
                <p className="text-xs text-muted-foreground">
                  目标金额：¥{s.target_value.toLocaleString()}
                </p>
              )}
              {s.market_value != null && (
                <p className="text-xs text-muted-foreground">
                  市值：¥{s.market_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </p>
              )}
              {s.pnl != null && (
                <p className={`text-xs ${s.pnl >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                  浮动盈亏：¥{s.pnl.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

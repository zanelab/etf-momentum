import { useMemo } from "react";

import { DEFENSIVE_REASON, usePool, useScreeningToday, useSignalsToday } from "@/api/hooks";

export default function Signals() {
  const signals = useSignalsToday();
  const screening = useScreeningToday();
  const pool = usePool();

  const data = signals.data;
  const sellList = useMemo(() => (data?.signals ?? []).filter((s) => s.type === "SELL"), [data]);
  const buyList = useMemo(() => (data?.signals ?? []).filter((s) => s.type === "BUY"), [data]);
  const isDefensive = buyList.length === 1 && buyList[0].reason === DEFENSIVE_REASON;

  const nameByCode = useMemo(() => {
    const map: Record<string, string> = {};
    for (const e of pool.data ?? []) {
      if (e.display_name) map[e.code] = e.display_name;
    }
    return map;
  }, [pool.data]);

  if (signals.isLoading) return <p>加载中…</p>;
  if (signals.isError) {
    return (
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">今日调仓</h2>
        <div className="rounded border border-rose-300 bg-rose-50 p-4 text-sm text-rose-900">
          今日信号暂不可用，请检查<a href="/datasource" className="underline">数据源</a>。
        </div>
      </section>
    );
  }
  if (!data) return null;

  const totalActions = sellList.length + buyList.length;

  const fullChecklist = [
    ...sellList.map((s) => `卖出 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`),
    ...buyList.map((s) => `买入 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`),
  ].join("\n");

  return (
    <section className="space-y-6">
      <header>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">📌 今日调仓 · {data.as_of}</h2>
          {totalActions > 0 && (
            <button
              type="button"
              onClick={() => navigator.clipboard?.writeText(fullChecklist)}
              className="rounded border bg-card px-3 py-1.5 text-xs underline"
            >
              📋 复制完整调仓清单
            </button>
          )}
        </div>
        {totalActions === 0 ? (
          <p className="mt-1 text-sm text-emerald-700">今天没有需要做的 ✓</p>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">
            本次需做 {totalActions} 项操作（卖出 {sellList.length} + 买入 {buyList.length}）
          </p>
        )}
      </header>

      {sellList.length > 0 && (
        <ActionTable
          tone="sell"
          rows={sellList.map((s) => ({
            code: s.etf,
            name: nameByCode[s.etf] ?? "—",
            label: `卖出 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`,
            cols: {
              "当前持仓": `${(s.shares ?? 0).toLocaleString()} 份`,
              "卖出数量": "全部",
              "估算金额": formatMoney(s.market_value),
            },
          }))}
        />
      )}

      {buyList.length > 0 && (
        <ActionTable
          tone="buy"
          rows={buyList.map((s) => ({
            code: s.etf,
            name: nameByCode[s.etf] ?? "—",
            label: `买入 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`,
            cols: {
              "目标金额": formatMoney(s.target_value),
              "买入数量": `${(s.shares ?? 0).toLocaleString()} 份`,
            },
          }))}
        />
      )}

      {isDefensive && (
        <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          ⚠ 防御模式：本次未发现满足动量条件的标的，资金转入 <code>511880.XSHG</code> 银华日利
        </div>
      )}

      {screening.data && screening.data.details && screening.data.details.length > 0 && (
        <details className="rounded border p-2 text-sm">
          <summary className="cursor-pointer">▶ 进阶：为什么这样选</summary>
          <table className="mt-2 w-full text-xs">
            <thead className="text-left opacity-70">
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>动量分</th>
                <th>年化收益</th>
                <th>R²</th>
                <th>量比</th>
              </tr>
            </thead>
            <tbody>
              {screening.data.details.map((d) => (
                <tr key={d.code} className="border-t border-current/10">
                  <td className="font-mono">{d.code}</td>
                  <td>{nameByCode[d.code] ?? "—"}</td>
                  <td>{(Math.round(d.momentum_score * 10000) / 10000).toFixed(4)}</td>
                  <td>{(d.annual_return * 100).toFixed(2)}%</td>
                  <td>{(Math.round(d.r2 * 10000) / 10000).toFixed(4)}</td>
                  <td>{d.volume_ratio === null ? "—" : (Math.round(d.volume_ratio * 10000) / 10000).toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      <details className="rounded border p-2 text-sm">
        <summary className="cursor-pointer">▶ 原始筛选输出</summary>
        <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(screening.data, null, 2)}</pre>
      </details>
    </section>
  );
}

function formatMoney(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(v);
}

interface ActionRow {
  code: string;
  name: string;
  label: string;
  cols: Record<string, string>;
}

function ActionTable({
  tone,
  rows,
}: {
  tone: "buy" | "sell";
  rows: ActionRow[];
}) {
  const headerClass = tone === "buy"
    ? "border-emerald-300 bg-emerald-50"
    : "border-rose-300 bg-rose-50";

  return (
    <div className={`rounded border p-3 ${headerClass}`}>
      <h3 className="mb-2 text-sm font-medium">
        <span aria-hidden>{tone === "buy" ? "🟢 " : "🔴 "}</span>
        {tone === "buy" ? "要买入的" : "要卖出的"}
        <span className="opacity-60"> ({rows.length})</span>
      </h3>
      <table className="w-full text-sm">
        <thead className="text-left text-xs opacity-70">
          <tr>
            <th>代码</th>
            <th>名称</th>
            {Object.keys(rows[0].cols).map((h) => (
              <th key={h}>{h}</th>
            ))}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.code} className="border-t border-current/10">
              <td className="font-mono">{r.code}</td>
              <td>{r.name}</td>
              {Object.entries(r.cols).map(([k, v]) => (
                <td key={k}>{v}</td>
              ))}
              <td>
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(r.label)}
                  className="text-xs underline"
                >
                  📋 复制
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

import { useMemo } from "react";
import { Link } from "react-router-dom";

import {
  DEFENSIVE_REASON,
  useDynamicPool,
  useHealthStats,
  usePool,
  usePortfolio,
  useScreeningToday,
  useSignalsToday,
} from "@/api/hooks";

function money(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(value);
}

export function Dashboard() {
  const portfolio = usePortfolio();
  const signals = useSignalsToday();
  const screening = useScreeningToday();
  const pool = usePool();
  const dynamicPool = useDynamicPool();
  const health = useHealthStats();

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

  const lastSync = dynamicPool.data && dynamicPool.data[0]?.last_synced_at
    ? new Date(dynamicPool.data[0].last_synced_at)
    : null;
  const isStale = lastSync !== null && (Date.now() - lastSync.getTime() > 24 * 60 * 60 * 1000);

  const totalActions = sellList.length + buyList.length;
  const fullChecklist = [
    ...sellList.map((s) => `卖出 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`),
    ...buyList.map((s) => `买入 ${s.etf} ${(s.shares ?? 0).toLocaleString()} 份`),
  ].join("\n");

  return (
    <div className="space-y-4">
      {/* 资产概览 */}
      <section className="rounded border bg-card p-4">
        <h2 className="text-lg font-semibold"><span aria-hidden>📊 </span>资产概览</h2>
        {portfolio.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {portfolio.isError && <p className="text-sm text-red-600">持仓数据暂不可用</p>}
        {portfolio.data && (
          <dl className="mt-2 grid grid-cols-2 gap-2 text-sm md:grid-cols-5">
            <Stat label="净值" value={money(portfolio.data.net_value)} />
            <Stat label="总市值" value={money(portfolio.data.total_market_value)} />
            <Stat label="成本" value={money(portfolio.data.total_cost)} />
            <Stat label="浮动盈亏" value={money(portfolio.data.total_pnl)} tone={portfolio.data.total_pnl >= 0 ? "pos" : "neg"} />
            <Stat label="可用资金" value={money(portfolio.data.available_cash)} />
          </dl>
        )}
      </section>

      {/* 今日调仓 (inlined from /signals) */}
      <section className="rounded border bg-card p-4">
        {signals.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {signals.isError && (
          <p className="text-sm text-red-600">信号暂不可用 <Link to="/datasource" className="underline">检查数据源</Link></p>
        )}
        {data && (
          <div className="space-y-4">
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
          </div>
        )}
      </section>

      {/* 系统状态 */}
      <section className="rounded border bg-card p-4">
        {isStale && (
          <div className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
            ⚠ 动态池已过期（&gt;24h），建议 <Link to="/dynamic-pool" className="underline">立即同步</Link>
          </div>
        )}
        <h2 className="text-lg font-semibold">系统状态</h2>
        {health.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {health.data && (
          <ul className="mt-2 space-y-1 text-sm">
            <li>
              数据源:{" "}
              {health.data.status === "ok" ? (
                <span className="text-emerald-700">● 在线</span>
              ) : (
                <span className="text-red-600">● 未连接</span>
              )}
            </li>
            {health.data.cache_hit !== undefined && (
              <li>
                缓存: {health.data.cache_hit}/{health.data.cache_miss !== undefined ? (health.data.cache_hit + health.data.cache_miss) : 0} hit
              </li>
            )}
            {dynamicPool.data && (
              <li>
                动态池: {dynamicPool.data.filter((d) => d.is_enabled).length} 已启用 /{" "}
                {dynamicPool.data.length} 总数
              </li>
            )}
            {dynamicPool.data && dynamicPool.data.length > 0 && (
              <li className="text-xs text-muted-foreground">
                上次同步:{" "}
                {new Date(dynamicPool.data[0].last_synced_at).toLocaleString("zh-CN")}
              </li>
            )}
          </ul>
        )}
        <Link to="/datasource" className="mt-2 inline-block text-xs underline">
          进入 →
        </Link>
      </section>

      {/* 当前持仓 (inlined from /portfolio) */}
      <section className="rounded border bg-card p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold"><span aria-hidden>📋 </span>当前持仓</h2>
        </div>
        {portfolio.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {portfolio.data && portfolio.data.holdings.length === 0 && (
          <p className="mt-2 text-sm text-muted-foreground">暂无持仓</p>
        )}
        {portfolio.data && portfolio.data.holdings.length > 0 && (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-2 py-1.5">代码</th>
                  <th className="px-2 py-1.5">名称</th>
                  <th className="px-2 py-1.5 text-right">持仓数量</th>
                  <th className="px-2 py-1.5 text-right">成本价</th>
                  <th className="px-2 py-1.5 text-right">现价</th>
                  <th className="px-2 py-1.5 text-right">市值</th>
                  <th className="px-2 py-1.5 text-right">浮动盈亏</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.data.holdings.map((h) => (
                  <tr key={h.code} className="border-t">
                    <td className="px-2 py-1.5 font-mono">{h.code}</td>
                    <td className="px-2 py-1.5">{nameByCode[h.code] ?? "—"}</td>
                    <td className="px-2 py-1.5 text-right">{h.shares.toLocaleString()}</td>
                    <td className="px-2 py-1.5 text-right">{h.cost_price.toFixed(2)}</td>
                    <td className="px-2 py-1.5 text-right">{h.current_price.toFixed(2)}</td>
                    <td className="px-2 py-1.5 text-right">{money(h.market_value)}</td>
                    <td className={`px-2 py-1.5 text-right ${h.pnl >= 0 ? "text-emerald-700" : "text-red-600"}`}>
                      {money(h.pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "pos" | "neg" }) {
  const toneClass = tone === "pos" ? "text-emerald-700" : tone === "neg" ? "text-red-600" : "";
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={`text-lg font-medium ${toneClass}`}>{value}</dd>
    </div>
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

export default Dashboard;

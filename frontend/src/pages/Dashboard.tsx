import { useMemo } from "react";
import { Link } from "react-router-dom";

import { useDynamicPool, useHealthStats, usePool, usePortfolio, useSignalsToday } from "@/api/hooks";

function money(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(value);
}

function pct(numerator: number, denominator: number): string {
  if (!denominator) return "—";
  const v = (numerator / denominator) * 100;
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function Dashboard() {
  const portfolio = usePortfolio();
  const signals = useSignalsToday();
  const pool = usePool();
  const dynamicPool = useDynamicPool();
  const health = useHealthStats();

  const nameByCode = useMemo(() => {
    const map: Record<string, string> = {};
    for (const e of pool.data ?? []) {
      if (e.display_name) map[e.code] = e.display_name;
    }
    return map;
  }, [pool.data]);

  const realSignals = (signals.data?.signals ?? []).filter(
    (s) => !(s.type === "BUY" && s.reason === "无动量目标，切换防御模式"),
  );
  const actionCount = realSignals.length;

  const lastSync = dynamicPool.data && dynamicPool.data[0]?.last_synced_at
    ? new Date(dynamicPool.data[0].last_synced_at)
    : null;
  const isStale = lastSync !== null && (Date.now() - lastSync.getTime() > 24 * 60 * 60 * 1000);

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

      {/* 今日需要做的 + 系统状态 */}
      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded border bg-card p-4 md:col-span-2">
          <h2 className="text-lg font-semibold"><span aria-hidden>⚡ </span>今日需要做的</h2>
          {signals.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
          {signals.isError && (
            <p className="text-sm text-red-600">
              信号暂不可用 <Link to="/datasource" className="underline">检查数据源</Link>
            </p>
          )}
          {signals.data && actionCount > 0 && (
            <div className="mt-2 space-y-2">
              <p className="text-sm">今天需要做 {actionCount} 项操作</p>
              <Link to="/signals" className="inline-block rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground">
                查看清单 →
              </Link>
            </div>
          )}
          {signals.data && actionCount === 0 && (
            <p className="mt-2 text-sm text-emerald-700">今日不需要调整 ✓</p>
          )}
        </section>

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
      </div>

      {/* 当前持仓 */}
      <section className="rounded border bg-card p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold"><span aria-hidden>📋 </span>当前持仓<span className="text-sm font-normal text-muted-foreground">（Top 5）</span></h2>
          {portfolio.data && portfolio.data.holdings.length > 0 && (
            <Link to="/portfolio" className="text-sm underline">查看全部持仓 →</Link>
          )}
        </div>
        {portfolio.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
        {portfolio.data && portfolio.data.holdings.length === 0 && (
          <p className="mt-2 text-sm text-muted-foreground">暂无持仓</p>
        )}
        {portfolio.data && portfolio.data.holdings.length > 0 && (
          <table className="mt-2 w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th>代码</th><th>名称</th><th>现价</th><th>数量</th><th>浮盈亏</th><th>比例</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.data.holdings.slice(0, 5).map((h) => (
                <tr key={h.code} className="border-t">
                  <td className="font-mono">{h.code}</td>
                  <td>{nameByCode[h.code] ?? "—"}</td>
                  <td>¥{h.current_price.toFixed(2)}</td>
                  <td>{h.shares.toLocaleString()}</td>
                  <td className={h.pnl >= 0 ? "text-emerald-700" : "text-red-600"}>
                    {money(h.pnl)}
                  </td>
                  <td className={h.pnl >= 0 ? "text-emerald-700" : "text-red-600"}>
                    {pct(h.pnl, h.cost_price * h.shares)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

export default Dashboard;

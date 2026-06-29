import { useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link, useParams } from "react-router-dom";

import { useDynamicPool, useMarketHistory } from "@/api/hooks";

const fmtDate = (s: string) => s.slice(5); // MM-DD

export default function EtfDetailPage() {
  const { code = "" } = useParams<{ code: string }>();
  const { data: pool } = useDynamicPool();
  const [start, setStart] = useState("2026-01-01");
  const [end, setEnd] = useState("2026-03-19");

  const history = useMarketHistory(
    code || null,
    start,
    end,
    ["open", "high", "low", "close", "volume"],
  );

  const inPool = pool?.some((e) => e.code === code) ?? false;
  const name = pool?.find((e) => e.code === code)?.name;

  return (
    <section className="space-y-4">
      <header className="flex items-center gap-3">
        <Link
          to="/dynamic-pool"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← 返回动态池
        </Link>
        <h2 className="text-lg font-semibold">
          {code}
          {name ? ` · ${name}` : ""}
        </h2>
      </header>

      {!inPool && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          该 ETF 已不在动态池中。以下 K 线数据来自 fixture mock，仅供参考。
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 rounded border p-4">
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">开始</span>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">结束</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
        </label>
      </div>

      {history.isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
      {history.error && (
        <p className="text-sm text-rose-600">加载失败：{String(history.error)}</p>
      )}

      {history.data && history.data.rows.length > 0 && (
        <div className="rounded border p-4">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            {code}
            {name ? ` · ${name}` : ""} · 收盘价 & 成交量
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={history.data.rows}>
              <CartesianGrid stroke="#eee" />
              <XAxis
                dataKey="date"
                tickFormatter={fmtDate}
                minTickGap={30}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11 }}
                domain={["auto", "auto"]}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => `${(v / 1e6).toFixed(0)}M`}
              />
              <Tooltip />
              <Bar
                yAxisId="right"
                dataKey="volume"
                fill="#cbd5e1"
                name="成交量"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="close"
                stroke="#2563eb"
                dot={false}
                name="收盘"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

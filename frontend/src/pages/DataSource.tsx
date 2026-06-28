// Data source health + dynamic pool management.
import { useMemo, useState } from "react";

import {
  useDynamicPool,
  useHealthStats,
  useSyncDynamicPool,
  useToggleDynamicEntry,
} from "@/api/hooks";

export default function DataSource() {
  const stats = useHealthStats();
  const pool = useDynamicPool();
  const sync = useSyncDynamicPool();
  const toggle = useToggleDynamicEntry();
  const [filter, setFilter] = useState("");

  const lastSyncedAt = useMemo(() => {
    const rows = pool.data ?? [];
    if (rows.length === 0) return null;
    const latest = rows
      .map((r) => r.last_synced_at)
      .sort()
      .pop();
    return latest ?? null;
  }, [pool.data]);

  const filtered = (pool.data ?? []).filter((e) =>
    `${e.code} ${e.name}`.toLowerCase().includes(filter.toLowerCase()),
  );

  const enabledCount = (pool.data ?? []).filter((e) => e.is_enabled).length;

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">数据源</h2>
        <p className="text-sm text-muted-foreground">
          显示当前行情源、缓存命中统计、动态池同步状态。
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="健康状态"
          value={stats.isLoading ? "…" : stats.data?.status ?? "unknown"}
        />
        <StatCard
          label="缓存命中"
          value={
            stats.data?.cache_hit !== undefined
              ? String(stats.data.cache_hit)
              : "n/a"
          }
        />
        <StatCard
          label="缓存未命中"
          value={
            stats.data?.cache_miss !== undefined
              ? String(stats.data.cache_miss)
              : "n/a"
          }
        />
      </div>

      <div className="rounded border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-medium">动态池</h3>
            <p className="text-xs text-muted-foreground">
              {(pool.data ?? []).length} 条记录 · {enabledCount} 已启用 · 最近同步：
              {lastSyncedAt ? new Date(lastSyncedAt).toLocaleString() : "—"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              className="rounded border px-3 py-1 text-sm"
              placeholder="筛选 code / 名称…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <button
              className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              disabled={sync.isPending}
              onClick={() => sync.mutate()}
            >
              {sync.isPending ? "同步中…" : "立即同步"}
            </button>
          </div>
        </div>
        {sync.isSuccess && (
          <p className="mt-2 text-xs text-muted-foreground">
            上次同步：synced={sync.data.synced}, total={sync.data.total},
            enabled={sync.data.enabled}
          </p>
        )}
        {sync.isError && (
          <p className="mt-2 text-xs text-red-600">
            同步失败：{String(sync.error)}
          </p>
        )}
      </div>

      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-left">名称</th>
              <th className="px-3 py-2 text-left">启用</th>
              <th className="px-3 py-2 text-left">最近同步</th>
            </tr>
          </thead>
          <tbody>
            {pool.isLoading && (
              <tr>
                <td className="px-3 py-2 text-muted-foreground" colSpan={4}>
                  加载中…
                </td>
              </tr>
            )}
            {pool.isError && (
              <tr>
                <td className="px-3 py-2 text-red-600" colSpan={4}>
                  加载失败：{String(pool.error)}
                </td>
              </tr>
            )}
            {filtered.length === 0 && !pool.isLoading && !pool.isError && (
              <tr>
                <td className="px-3 py-2 text-muted-foreground" colSpan={4}>
                  暂无记录。点击「立即同步」从数据源拉取。
                </td>
              </tr>
            )}
            {filtered.map((e) => (
              <tr key={e.code} className="border-t">
                <td className="px-3 py-1.5 font-mono">{e.code}</td>
                <td className="px-3 py-1.5">{e.name}</td>
                <td className="px-3 py-1.5">
                  <input
                    type="checkbox"
                    checked={e.is_enabled}
                    disabled={toggle.isPending}
                    onChange={(ev) =>
                      toggle.mutate({ code: e.code, isEnabled: ev.target.checked })
                    }
                  />
                </td>
                <td className="px-3 py-1.5 text-xs text-muted-foreground">
                  {new Date(e.last_synced_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
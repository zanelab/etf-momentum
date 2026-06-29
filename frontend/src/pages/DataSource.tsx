// Data source health + dynamic pool management.
import { useHealthStats } from "@/api/hooks";

export default function DataSource() {
  const stats = useHealthStats();

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">数据源</h2>
        <p className="text-sm text-muted-foreground">
          显示当前行情源、缓存命中统计。
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
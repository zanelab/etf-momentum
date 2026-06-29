import { SyncStatusBadge } from "@/components/SyncStatusBadge";
import { useSyncStatus, useTriggerSync } from "@/api/hooks";

export function SyncStatus() {
  const { data, isLoading, isError } = useSyncStatus();
  const trigger = useTriggerSync();

  const etfs = data?.etfs ?? [];
  const isEmpty = !isLoading && etfs.length === 0;

  return (
    <section className="space-y-4 p-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">数据同步</h1>
          <p className="text-sm text-muted-foreground">
            上次同步：{data?.as_of ?? "—"}
          </p>
        </div>
        <button
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending || etfs.length === 0}
          className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {trigger.isPending ? "同步中…" : "立即同步"}
        </button>
      </header>

      {isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
      {isError && <p className="text-sm text-red-600">同步状态暂不可用</p>}
      {isEmpty && <p className="text-sm text-muted-foreground">暂无 ETF</p>}

      {etfs.length > 0 && (
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50 text-left">
            <tr>
              <th className="px-2 py-1">代码</th>
              <th className="px-2 py-1">名称</th>
              <th className="px-2 py-1">同步日期</th>
              <th className="px-2 py-1">状态</th>
            </tr>
          </thead>
          <tbody>
            {etfs.map((e) => (
              <tr key={e.code} className="border-b">
                <td className="px-2 py-1 font-mono">{e.code}</td>
                <td className="px-2 py-1">{e.name ?? "—"}</td>
                <td className="px-2 py-1">{e.last_synced_date ?? "—"}</td>
                <td className="px-2 py-1">
                  <SyncStatusBadge status={e.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

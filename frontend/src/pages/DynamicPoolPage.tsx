import { useDynamicPool, useSyncDynamicPool, useToggleDynamicEntry } from "@/api/hooks";

export default function DynamicPoolPage() {
  const { data, isLoading, isError } = useDynamicPool();
  const sync = useSyncDynamicPool();
  const toggle = useToggleDynamicEntry();

  if (isLoading) return <p>加载中…</p>;
  if (isError) return <p className="text-red-600">加载失败</p>;

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">动态池</h2>
        <button
          type="button"
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
          className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {sync.isPending ? "同步中…" : "重新同步"}
        </button>
      </header>

      {data && data.length === 0 && <p className="text-sm text-muted-foreground">暂无条目，请点击「重新同步」</p>}

      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th>代码</th><th>名称</th><th>启用</th><th>上次同步</th>
            </tr>
          </thead>
          <tbody>
            {data.map((e) => (
              <tr key={e.code} className="border-t">
                <td className="font-mono">{e.code}</td>
                <td>{e.name}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={e.is_enabled}
                    onChange={(ev) =>
                      toggle.mutate({ code: e.code, isEnabled: ev.target.checked })
                    }
                  />
                </td>
                <td className="text-xs text-muted-foreground">
                  {new Date(e.last_synced_at).toLocaleString("zh-CN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
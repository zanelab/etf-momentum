// Static pool configuration: table view with enable/disable toggle + delete.
import { useState } from "react";

import {
  useDeletePoolEntry,
  usePool,
  useUpdatePoolEntry,
} from "@/api/hooks";

export default function PoolConfig() {
  const pool = usePool();
  const update = useUpdatePoolEntry();
  const del = useDeletePoolEntry();
  const [filter, setFilter] = useState("");

  if (pool.isLoading) return <p>加载中…</p>;
  if (pool.error) return <p className="text-red-600">加载失败：{String(pool.error)}</p>;
  const entries = (pool.data ?? []).filter((e) =>
    e.code.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <section>
      <header className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">静态池（{(pool.data ?? []).length}）</h2>
        <input
          className="rounded border px-3 py-1 text-sm"
          placeholder="筛选 code…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </header>
      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-left">名称</th>
              <th className="px-3 py-2 text-left">启用</th>
              <th className="px-3 py-2 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.code} className="border-t">
                <td className="px-3 py-1.5 font-mono">{e.code}</td>
                <td className="px-3 py-1.5">{e.display_name ?? "—"}</td>
                <td className="px-3 py-1.5">
                  <input
                    type="checkbox"
                    checked={e.enabled}
                    onChange={(ev) =>
                      update.mutate({ code: e.code, body: { enabled: ev.target.checked } })
                    }
                  />
                </td>
                <td className="px-3 py-1.5">
                  <button
                    className="text-xs text-red-600 hover:underline"
                    onClick={() => {
                      if (confirm(`删除 ${e.code}？`)) del.mutate(e.code);
                    }}
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

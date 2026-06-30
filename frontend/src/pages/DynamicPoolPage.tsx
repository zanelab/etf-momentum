import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCancelSync, useDynamicPool, useSyncDynamicPool, useSyncStatus, useToggleDynamicEntry, useTriggerSync } from "@/api/hooks";
import { DateRangePicker } from "@/components/DateRangePicker";
import { RowProgressBar } from "@/components/RowProgressBar";
import { SyncProgressBanner } from "@/components/SyncProgressBanner";
import { SyncStatusBadge } from "@/components/SyncStatusBadge";

export default function DynamicPoolPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useDynamicPool();
  const syncPool = useSyncDynamicPool();
  const syncHistory = useTriggerSync();
  const cancelSync = useCancelSync();
  const toggle = useToggleDynamicEntry();
  const syncStatus = useSyncStatus();

  const [pickerOpen, setPickerOpen] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const isPoolEmpty = (data?.length ?? 0) === 0;
  const isRunning = syncStatus.data?.is_running ?? false;
  const isCancelled = syncStatus.data?.is_cancelled ?? false;
  const inProgress = syncStatus.data?.in_progress ?? [];
  const anyPending = syncPool.isPending || syncHistory.isPending || isRunning;

  const statusByCode = new Map((syncStatus.data?.etfs ?? []).map((e) => [e.code, e.status]));
  const progressByCode = new Map(inProgress.map((p) => [p.code, p]));

  if (isLoading) return <p>加载中…</p>;
  if (isError) return <p className="text-red-600">加载失败</p>;

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">动态池</h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => syncPool.mutate()}
            disabled={anyPending}
            className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            {syncPool.isPending ? "同步中…" : "同步 ETF"}
          </button>
          <button
            type="button"
            onClick={() => {
              setSyncError(null);
              setPickerOpen(true);
            }}
            disabled={anyPending || isPoolEmpty}
            className="rounded border bg-background px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {syncHistory.isPending ? "同步中…" : "同步 ETF 历史数据"}
          </button>
        </div>
      </header>

      {inProgress.length > 0 && <SyncProgressBanner progress={inProgress} isCancelled={isCancelled} />}

      {inProgress.length > 0 && !isCancelled && (
        <div>
          <button
            type="button"
            onClick={() => cancelSync.mutate()}
            disabled={cancelSync.isPending}
            className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700 disabled:opacity-50"
            data-testid="cancel-sync-button"
          >
            取消
          </button>
        </div>
      )}

      {isPoolEmpty && !anyPending && (
        <p className="text-sm text-muted-foreground">暂无动态池条目，请点击「同步 ETF」拉取全市场 ETF 列表</p>
      )}

      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th>代码</th>
              <th>名称</th>
              <th>启用</th>
              <th>上次同步</th>
              <th>历史同步状态</th>
            </tr>
          </thead>
          <tbody>
            {data.map((e) => (
              <tr
                key={e.code}
                onClick={() => navigate("/dynamic-pool/" + encodeURIComponent(e.code))}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter") navigate("/dynamic-pool/" + encodeURIComponent(e.code));
                }}
                tabIndex={0}
                className="cursor-pointer border-t hover:bg-accent/30"
                data-testid={`pool-row-${e.code}`}
              >
                <td className="font-mono">{e.code}</td>
                <td>{e.name}</td>
                <td onClick={(ev) => ev.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={e.is_enabled}
                    onChange={(ev) => toggle.mutate({ code: e.code, isEnabled: ev.target.checked })}
                  />
                </td>
                <td className="text-xs text-muted-foreground">
                  {e.last_synced_at ? new Date(e.last_synced_at).toLocaleString("zh-CN") : "—"}
                </td>
                <td>
                  {progressByCode.get(e.code) ? (
                    <RowProgressBar info={progressByCode.get(e.code)!} />
                  ) : (
                    <SyncStatusBadge status={statusByCode.get(e.code) ?? "never"} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <DateRangePicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onConfirm={(range) => {
          setSyncError(null);
          syncHistory.mutate(range, {
            onSuccess: () => setPickerOpen(false),
            onError: (err) => setSyncError(err.message),
          });
        }}
        isSubmitting={syncHistory.isPending}
        errorMessage={syncError}
      />
    </section>
  );
}
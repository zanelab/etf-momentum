import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  useCancelSync,
  useDynamicPoolWithStatus,
  useSyncDynamicPool,
  useToggleDynamicEntry,
  useTriggerSync,
} from "@/api/hooks";
import { DateRangePicker } from "@/components/DateRangePicker";
import { RowProgressBar } from "@/components/RowProgressBar";
import { SyncProgressBanner } from "@/components/SyncProgressBanner";
import { SyncStatusBadge } from "@/components/SyncStatusBadge";

export default function DynamicPoolPage() {
  const navigate = useNavigate();
  const { data: status, isLoading, isError } = useDynamicPoolWithStatus();
  const syncPool = useSyncDynamicPool();
  const syncHistory = useTriggerSync();
  const cancelSync = useCancelSync();
  const toggle = useToggleDynamicEntry();

  const [pickerOpen, setPickerOpen] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Derived state from the single status response
  const etfs = status?.etfs ?? [];
  const inProgress = status?.in_progress ?? [];
  const poolRunning = syncPool.isPending;
  const historyRunning = status?.is_running ?? false;
  const historyJustStarted = syncHistory.isPending;
  const cancelInFlight = cancelSync.isPending;
  const isPoolEmpty = etfs.length === 0;

  // "同步 ETF" button: mutex — disabled whenever any sync is active
  // (history running OR pool syncing). This is the hard gate.
  const syncEtfDisabled = poolRunning || historyRunning;

  // "同步 ETF 历史数据" button state machine.
  //
  // State | historyRunning | historyJustStarted | cancelInFlight
  // -------+----------------+--------------------+---------------
  //   idle |     false      |       false        |   * (implied false)
  // starting|     false      |       true         |   false
  // running|     true       |       *            |   false
  //   cancelling| true     |       *            |   true
  //
  // label / onClick / disabled are derived from the row above.
  const historyBtnLabel =
    historyRunning
      ? (cancelInFlight ? "取消中…" : "取消")
      : historyJustStarted
        ? "同步中…"
        : "同步 ETF 历史数据";

  const historyBtnDisabled =
    historyRunning
      ? cancelInFlight
      : historyJustStarted
        ? true
        : poolRunning || isPoolEmpty;

  // Per-row maps (used by the table)
  const statusByCode = new Map(etfs.map((e) => [e.code, e.status]));
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
            disabled={syncEtfDisabled}
            className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            {poolRunning ? "同步中…" : "同步 ETF"}
          </button>
          <button
            type="button"
            onClick={() => {
              if (historyRunning) {
                cancelSync.mutate();
              } else {
                setSyncError(null);
                setPickerOpen(true);
              }
            }}
            disabled={historyBtnDisabled}
            className="rounded border bg-background px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {historyBtnLabel}
          </button>
        </div>
      </header>

      {inProgress.length > 0 && <SyncProgressBanner progress={inProgress} />}

      {isPoolEmpty && !syncEtfDisabled && !historyRunning && !historyJustStarted && (
        <p className="text-sm text-muted-foreground">暂无动态池条目，请点击「同步 ETF」拉取全市场 ETF 列表</p>
      )}

      {etfs.length > 0 && (
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
            {etfs.map((e) => (
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
                    (() => {
                      // progress bar is shown for in_progress codes; for the rest,
                      // map the status to the badge's accepted set.
                      const s = statusByCode.get(e.code) ?? "never";
                      const badgeStatus: "ok" | "failed" | "missing" | "never" =
                        s === "in_progress" ? "never" : s;
                      return <SyncStatusBadge status={badgeStatus} />;
                    })()
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

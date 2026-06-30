import type { ProgressInfo } from "@/api/hooks";

export function SyncProgressBanner({
  progress,
  isCancelled = false,
}: {
  progress: ProgressInfo[];
  isCancelled?: boolean;
}) {
  if (progress.length === 0) return null;

  const total = progress[0].overall_total;
  const done = Math.max(...progress.map((p) => p.overall_index));
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  // Show the most recently updated code (largest overall_index)
  const current = progress.reduce((a, b) => (a.overall_index >= b.overall_index ? a : b));

  const bgColor = isCancelled ? "bg-red-50 border-red-300" : "bg-blue-50";
  const barColor = isCancelled ? "bg-red-500" : "bg-blue-500";
  const headerText = isCancelled ? "已取消" : "同步进行中";

  return (
    <div className={`rounded border p-3 text-sm ${bgColor}`} data-testid="sync-progress-banner">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-medium">{headerText}</span>
        <span className="text-muted-foreground">{done} / {total} ({percent}%)</span>
      </div>
      <div className={`mb-2 h-2 w-full overflow-hidden rounded ${isCancelled ? "bg-red-100" : "bg-blue-100"}`}>
        <div className={`h-full transition-all ${barColor}`} style={{ width: `${percent}%` }} />
      </div>
      <div className="text-xs text-muted-foreground">
        {isCancelled ? "已同步" : "当前"}：<span className="font-mono">{current.code}</span>{" "}
        {current.current_date} / 共 {current.total_days} 天
      </div>
    </div>
  );
}
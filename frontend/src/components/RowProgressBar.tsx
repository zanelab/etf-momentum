import type { ProgressInfo } from "@/api/hooks";

export function RowProgressBar({ info }: { info: ProgressInfo }) {
  const pct = info.total_days > 0
    ? Math.round((info.completed_days / info.total_days) * 100)
    : 0;

  return (
    <div className="flex flex-col gap-1" data-testid="row-progress-bar">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-mono">{info.current_date}</span>
        <span>/</span>
        <span>共 {info.total_days} 天</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 w-full overflow-hidden rounded bg-blue-100"
      >
        <div className="h-full bg-blue-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
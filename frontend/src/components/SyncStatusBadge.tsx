export type SyncStatusValue = "ok" | "failed" | "missing" | "never";

const LABEL: Record<SyncStatusValue, string> = {
  ok: "✓ 已同步",
  failed: "⚠ 失败",
  missing: "— 缺失",
  never: "— 未同步",
};

const CLASS: Record<SyncStatusValue, string> = {
  ok: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  missing: "bg-gray-100 text-gray-600",
  never: "bg-gray-100 text-gray-600",
};

export function SyncStatusBadge({ status }: { status: SyncStatusValue }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs ${CLASS[status]}`}>
      {LABEL[status]}
    </span>
  );
}
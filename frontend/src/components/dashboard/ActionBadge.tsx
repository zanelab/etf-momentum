import { cn } from "@/lib/utils";

const TONE: Record<string, string> = {
  BUY: "bg-emerald-100 text-emerald-700 ring-emerald-600/20",
  HOLD: "bg-sky-100 text-sky-700 ring-sky-600/20",
  WATCH: "bg-slate-100 text-slate-700 ring-slate-600/20",
};

const FALLBACK = "bg-slate-100 text-slate-700 ring-slate-600/20";

export function ActionBadge({ action }: { action: string }) {
  const tone = TONE[action] ?? FALLBACK;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        tone,
      )}
    >
      {action}
    </span>
  );
}

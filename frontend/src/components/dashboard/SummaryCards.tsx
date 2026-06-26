export interface SummaryCardsProps {
  date: string | null;
  total: number;
  counts: { BUY: number; HOLD: number; WATCH: number };
}

interface CardProps {
  label: string;
  value: string | number;
  tone?: string;
}

function Card({ label, value, tone = "bg-card" }: CardProps) {
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${tone}`}>
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

export function SummaryCards({ date, total, counts }: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <Card label="Snapshot 日期" value={date ?? "—"} />
      <Card label="ETF 总数" value={total} />
      <Card
        label="BUY"
        value={counts.BUY}
        tone="bg-emerald-50 border-emerald-200"
      />
      <Card
        label="HOLD"
        value={counts.HOLD}
        tone="bg-sky-50 border-sky-200"
      />
      <Card
        label="WATCH"
        value={counts.WATCH}
        tone="bg-slate-50 border-slate-200"
      />
    </div>
  );
}

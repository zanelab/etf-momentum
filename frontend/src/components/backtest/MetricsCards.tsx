import type { BacktestMetrics } from "@/api/backtest";

export interface MetricsCardsProps {
  metrics: BacktestMetrics | null;
}

interface MetricConfig {
  key: keyof BacktestMetrics | "calmar_ratio";
  label: string;
  format: "percent" | "ratio";
}

const METRICS: MetricConfig[] = [
  { key: "total_return", label: "总收益", format: "percent" },
  { key: "annualized_return", label: "年化收益", format: "percent" },
  { key: "max_drawdown", label: "最大回撤", format: "percent" },
  { key: "sharpe_ratio", label: "夏普比率", format: "ratio" },
  { key: "sortino_ratio", label: "Sortino", format: "ratio" },
  { key: "calmar_ratio", label: "Calmar", format: "ratio" },
];

const PLACEHOLDER = "—";

function formatValue(raw: unknown, format: MetricConfig["format"]): string {
  if (raw === null || raw === undefined || raw === "") return PLACEHOLDER;
  const num = typeof raw === "number" ? raw : Number(raw);
  if (!Number.isFinite(num)) return PLACEHOLDER;
  if (format === "percent") return `${(num * 100).toFixed(2)}%`;
  return num.toFixed(3);
}

export function MetricsCards({ metrics }: MetricsCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {METRICS.map((metric) => {
        const raw = metrics ? metrics[metric.key] : undefined;
        return (
          <div
            key={metric.key}
            className="rounded-lg border bg-card p-4 shadow-sm"
            data-testid={`metric-${metric.key}`}
          >
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {metric.label}
            </div>
            <div className="mt-2 text-2xl font-semibold">
              {formatValue(raw, metric.format)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

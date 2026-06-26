import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { NavPoint } from "@/api/backtest";

export interface NavChartProps {
  data: NavPoint[];
  loading?: boolean;
  errorMessage?: string | null;
  width?: number | string;
  height?: number | string;
}

interface ChartDatum {
  date: string;
  displayDate: string;
  nav: number;
}

function toChartData(data: NavPoint[]): ChartDatum[] {
  return data.map((point) => ({
    date: point.date,
    displayDate: point.date,
    nav: Number(point.nav),
  }));
}

function formatDate(value: string): string {
  return value;
}

function formatNav(value: number): string {
  return value.toLocaleString();
}

export function NavChart({
  data,
  loading = false,
  errorMessage = null,
  width = "100%",
  height = 320,
}: NavChartProps) {
  if (loading) {
    return (
      <div
        className="flex h-80 items-center justify-center rounded-lg border bg-card shadow-sm"
        data-testid="nav-chart-loading"
      >
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-muted border-t-primary" />
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div
        className="flex h-40 flex-col items-center justify-center rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700"
        data-testid="nav-chart-error"
      >
        <div className="text-sm font-medium">NAV 数据加载失败</div>
        <div className="mt-1 text-xs">{errorMessage}</div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className="flex h-40 items-center justify-center rounded-lg border bg-card text-sm text-muted-foreground shadow-sm"
        data-testid="nav-chart-empty"
      >
        暂无 NAV 数据
      </div>
    );
  }

  const chartData = toChartData(data);

  const numericWidth = typeof width === "number" ? width : 0;
  const numericHeight = typeof height === "number" ? height : 0;

  return (
    <div
      className="rounded-lg border bg-card p-3 shadow-sm"
      data-testid="nav-chart"
    >
      <ResponsiveContainer
        width={numericWidth > 0 ? numericWidth : "100%"}
        height={numericHeight > 0 ? numericHeight : "100%"}
      >
        <LineChart data={chartData} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="displayDate" tickFormatter={formatDate} tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={formatNav} tick={{ fontSize: 12 }} width={80} />
          <Tooltip
            formatter={(value) => {
              const num = typeof value === "number" ? value : Number(value);
              return [Number.isFinite(num) ? formatNav(num) : String(value), "NAV"];
            }}
            labelFormatter={(label) => `日期: ${String(label ?? "")}`}
          />
          <Line
            type="monotone"
            dataKey="nav"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

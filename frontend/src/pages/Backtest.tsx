// Backtest page: date pickers, run button, status polling, NAV chart, stats.
import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  useBacktestTask,
  useStartBacktest,
} from "@/api/hooks";

const fmtPct = (n: number) => `${(n * 100).toFixed(2)}%`;

export default function Backtest() {
  const [start, setStart] = useState("2026-01-01");
  const [end, setEnd] = useState("2026-03-01");
  const [taskId, setTaskId] = useState<string | null>(null);

  const startMutation = useStartBacktest();
  const task = useBacktestTask(taskId);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    startMutation.mutate(
      { start, end },
      { onSuccess: (res) => setTaskId(res.task_id) },
    );
  };

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">回测</h2>
      </header>
      <form
        onSubmit={onSubmit}
        className="flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">开始日期</span>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">结束日期</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={startMutation.isPending || task.data?.status === "running"}
          className="rounded bg-primary px-4 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {startMutation.isPending || task.data?.status === "running"
            ? "提交中…"
            : "开始回测"}
        </button>
        {startMutation.error && (
          <span className="text-sm text-rose-600">
            提交失败：{String((startMutation.error as Error).message)}
          </span>
        )}
      </form>

      {task.data && (
        <TaskPanel
          status={task.data.status}
          error={task.data.error}
          result={task.data.result}
        />
      )}
    </section>
  );
}

function TaskPanel({
  status,
  error,
  result,
}: {
  status: string;
  error?: string;
  result: NonNullable<
    ReturnType<typeof useBacktestTask>["data"]
  >["result"];
}) {
  if (status === "running") {
    return <p className="text-sm text-muted-foreground">计算中…</p>;
  }
  if (status === "failed") {
    return <p className="text-sm text-rose-600">失败：{error}</p>;
  }
  if (!result) return null;
  const s = result.stats;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="总收益" value={fmtPct(s.total_return)} tone={s.total_return >= 0 ? "pos" : "neg"} />
        <Stat label="年化收益" value={fmtPct(s.annualized_return)} tone={s.annualized_return >= 0 ? "pos" : "neg"} />
        <Stat label="夏普比率" value={s.sharpe.toFixed(2)} />
        <Stat label="最大回撤" value={fmtPct(s.max_drawdown)} tone="neg" />
      </div>
      <div className="rounded border p-4">
        <h3 className="mb-2 text-sm font-medium text-muted-foreground">净值曲线</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={result.nav_series}>
            <CartesianGrid stroke="#eee" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={30} />
            <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
            <Tooltip />
            <Line type="monotone" dataKey="nav" stroke="#2563eb" dot={false} />
          </LineChart>
        </ResponsiveContainer>
        <p className="mt-2 text-xs text-muted-foreground">
          交易日 {s.trading_days} · 调仓 {s.n_rebalances} 次 · 最终净值 {s.final_nav.toFixed(4)}
        </p>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg";
}) {
  return (
    <div className="rounded border p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold ${
          tone === "pos" ? "text-emerald-700" : tone === "neg" ? "text-rose-700" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}

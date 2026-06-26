import { useEffect } from "react";

import { BacktestForm } from "@/components/backtest/BacktestForm";
import { MetricsCards } from "@/components/backtest/MetricsCards";
import { NavChart } from "@/components/backtest/NavChart";
import type { BacktestRequest } from "@/api/backtest";
import { useBacktestStore } from "@/stores/backtest-store";
import { useEtfsStore } from "@/stores/etfs-store";

export function BacktestPage() {
  const etfsState = useEtfsStore();
  const backtestState = useBacktestStore();

  useEffect(() => {
    void etfsState.fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (req: BacktestRequest) => {
    void backtestState.submit(req);
  };

  const etfs = etfsState.data?.items ?? [];

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">回测</h2>
        <p className="text-sm text-muted-foreground">
          选择 ETF 池和参数，运行动量策略回测并查看业绩与净值曲线
        </p>
      </div>

      <BacktestForm
        etfs={etfs}
        etfsLoading={etfsState.status === "loading" || etfsState.status === "idle"}
        etfsError={etfsState.status === "error" ? etfsState.error : null}
        disabled={backtestState.submitStatus === "loading"}
        formErrors={backtestState.formErrors}
        onSubmit={handleSubmit}
      />

      <BacktestResultArea state={backtestState} />
    </section>
  );
}

interface BacktestResultAreaProps {
  state: ReturnType<typeof useBacktestStore.getState>;
}

function BacktestResultArea({ state }: BacktestResultAreaProps) {
  const { submitStatus, currentRun, navStatus, navSeries, navError, submitError } = state;

  if (submitStatus === "idle") {
    return (
      <div
        className="rounded-lg border bg-card p-6 text-sm text-muted-foreground shadow-sm"
        data-testid="result-empty"
      >
        提交表单后此处展示回测结果
      </div>
    );
  }

  if (submitStatus === "loading") {
    return (
      <div
        className="flex items-center gap-3 rounded-lg border bg-card p-6 text-sm text-muted-foreground shadow-sm"
        data-testid="result-submitting"
      >
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-muted border-t-primary" />
        正在运行回测…
      </div>
    );
  }

  if (submitStatus === "error") {
    return (
      <div
        className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 shadow-sm"
        data-testid="result-error"
      >
        <div className="font-medium">回测失败</div>
        {submitError && <div className="mt-1">{submitError}</div>}
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="result-success">
      {currentRun && (
        <div className="text-xs text-muted-foreground" data-testid="result-meta">
          BacktestRun #{currentRun.id} · {currentRun.start_date} → {currentRun.end_date} · 调仓频率 {currentRun.rebalance_freq}
        </div>
      )}
      <MetricsCards metrics={currentRun?.metrics ?? null} />
      <NavChart
        data={navSeries}
        loading={navStatus === "loading"}
        errorMessage={navStatus === "error" ? navError : null}
      />
    </div>
  );
}

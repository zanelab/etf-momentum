import { useEffect, useMemo } from "react";

import { EmptyState } from "@/components/dashboard/EmptyState";
import { SignalRankingTable } from "@/components/dashboard/SignalRankingTable";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { useEtfsStore } from "@/stores/etfs-store";
import { useSignalsStore } from "@/stores/signals-store";
import type { EtfItem } from "@/api/etfs";
import type { SignalRow } from "@/api/signals";

function countByAction(rows: SignalRow[]): { BUY: number; HOLD: number; WATCH: number } {
  return rows.reduce(
    (acc, r) => {
      if (r.action === "BUY" || r.action === "HOLD" || r.action === "WATCH") {
        acc[r.action] += 1;
      }
      return acc;
    },
    { BUY: 0, HOLD: 0, WATCH: 0 },
  );
}

export function DashboardPage() {
  const signalsState = useSignalsStore();
  const etfsState = useEtfsStore();

  useEffect(() => {
    void signalsState.fetchLatest();
    void etfsState.fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isLoading = signalsState.status === "loading" || etfsState.status === "loading";

  const etfDict = useMemo<Map<string, EtfItem>>(() => {
    const map = new Map<string, EtfItem>();
    if (etfsState.data) {
      for (const etf of etfsState.data.items) {
        map.set(etf.code, etf);
      }
    }
    return map;
  }, [etfsState.data]);

  if (isLoading) {
    return (
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">动量看板</h2>
        <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground shadow-sm">
          加载中...
        </div>
      </section>
    );
  }

  if (signalsState.status === "error") {
    return (
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">动量看板</h2>
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-6 text-sm text-destructive shadow-sm">
          <div className="font-medium">信号加载失败</div>
          <div className="mt-1">{signalsState.error}</div>
        </div>
      </section>
    );
  }

  const rows = signalsState.data?.rows ?? [];
  const date = signalsState.data?.date ?? null;
  const counts = countByAction(rows);
  const total = etfsState.status === "ok" && etfsState.data ? etfsState.data.total : rows.length;

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">动量看板</h2>
        <p className="text-sm text-muted-foreground">
          最近一个交易日的动量排名与调仓建议
        </p>
      </div>

      <SummaryCards date={date} total={total} counts={counts} />

      {rows.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {etfsState.status === "error" && (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
              ETF 字典加载失败：{etfsState.error}。名称/类别列已降级显示。
            </div>
          )}
          <SignalRankingTable rows={rows} etfDict={etfDict} />
        </>
      )}
    </section>
  );
}

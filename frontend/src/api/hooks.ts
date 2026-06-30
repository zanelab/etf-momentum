// TanStack Query hooks for every backend endpoint.
// Polling cadence: signals/portfolio 5s, backtest 2s.

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./client";

// ────────────── Types ──────────────

export type StaticPoolEntry = {
  code: string;
  display_name: string | null;
  enabled: boolean;
};

export type StaticPoolReplace = { entries: StaticPoolEntry[] };
export type StaticPoolUpdate = { enabled?: boolean; display_name?: string };

export type ThemeDictionary = { themes: Record<string, string[]> };
export type StrategyParams = { params: Record<string, unknown> };

export type ScreeningTargetDetail = {
  code: string;
  momentum_score: number;
  annual_return: number;
  r2: number;
  volume_ratio: number | null;
};

export type ScreeningToday = {
  as_of: string;
  targets: string[];
  details: ScreeningTargetDetail[];
};

// Shared constant for the defensive-mode BUY signal reason (spec §5.3).
// Imported by Dashboard.tsx so the literal string lives in one place.
export const DEFENSIVE_REASON = "无动量目标，切换防御模式";

export type PortfolioHolding = {
  code: string;
  shares: number;
  cost_price: number;
  current_price: number;
  market_value: number;
  pnl: number;
};

export type Portfolio = {
  as_of: string;
  total_market_value: number;
  total_cost: number;
  total_pnl: number;
  available_cash: number;
  net_value: number;
  holdings: PortfolioHolding[];
};

export type Signal = {
  type: "BUY" | "SELL";
  etf: string;
  reason: string;
  shares: number | null;
  target_value: number | null;
  market_value: number | null;
  pnl: number | null;
};

export type SignalsToday = { as_of: string; signals: Signal[] };

export type BacktestStats = {
  initial_nav: number;
  final_nav: number;
  total_return: number;
  annualized_return: number;
  sharpe: number;
  max_drawdown: number;
  trading_days: number;
  n_rebalances: number;
};

export type BacktestTask = {
  task_id: string;
  status: "running" | "completed" | "failed";
  created_at: string;
  request: { start: string; end: string };
  result:
    | null
    | {
        start: string;
        end: string;
        stats: BacktestStats;
        nav_series: { date: string; nav: number; daily_return: number }[];
      };
  error?: string;
};

export type MarketListResponse = {
  etfs: { code: string; display_name: string | null }[];
};

export type MarketHistoryResponse = {
  code: string;
  start: string;
  end: string;
  fields: string[];
  rows: { date: string; [k: string]: number | string | null }[];
};

export type DataSourceStats = {
  status: "ok";
  cache_hit?: number;
  cache_miss?: number;
};

export type DynamicPoolEntry = {
  code: string;
  name: string;
  is_enabled: boolean;
  last_synced_at: string;
};

export type DynamicPoolSyncResult = {
  synced: number;
  total: number;
  enabled: number;
};

export type SyncETFStatus = {
  code: string;
  name: string | null;
  last_synced_date: string | null;
  status: "ok" | "failed" | "missing" | "never";
  error: string | null;
};

// ProgressInfo: mirror of backend/app/services/sync_progress.py:ProgressInfo.
// Kept in sync by hand (no OpenAPI codegen in this project).
export interface ProgressInfo {
  code: string;
  from_date: string;
  to_date: string;
  current_date: string;
  total_days: number;
  completed_days: number;
  overall_index: number;
  overall_total: number;
  started_at: string;
}

export type SyncStatusResponse = {
  as_of: string | null;
  etfs: SyncETFStatus[];
  in_progress: ProgressInfo[] | null;
  is_running: boolean;
};

export type SyncTriggerResult = SyncStatusResponse & {
  synced_count: number;
  run_at: string;
};

// ────────────── Configs ──────────────

export function usePool() {
  return useQuery({
    queryKey: ["pool"],
    queryFn: () => api<StaticPoolEntry[]>("/api/configs/pool"),
  });
}

export function useReplacePool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entries: StaticPoolEntry[]) =>
      api<StaticPoolEntry[]>("/api/configs/pool", {
        method: "POST",
        body: JSON.stringify({ entries }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pool"] }),
  });
}

export function useUpdatePoolEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, body }: { code: string; body: StaticPoolUpdate }) =>
      api<StaticPoolEntry>(`/api/configs/pool/${encodeURIComponent(code)}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pool"] }),
  });
}

export function useDeletePoolEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      api<void>(`/api/configs/pool/${encodeURIComponent(code)}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pool"] }),
  });
}

export function useThemes() {
  return useQuery({
    queryKey: ["themes"],
    queryFn: () => api<ThemeDictionary>("/api/configs/themes"),
  });
}

export function useReplaceThemes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (themes: Record<string, string[]>) =>
      api<ThemeDictionary>("/api/configs/themes", {
        method: "PUT",
        body: JSON.stringify({ themes }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["themes"] }),
  });
}

export function useStrategy() {
  return useQuery({
    queryKey: ["strategy"],
    queryFn: () => api<StrategyParams>("/api/configs/strategy"),
  });
}

export function useUpdateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: Record<string, unknown>) =>
      api<StrategyParams>("/api/configs/strategy", {
        method: "PUT",
        body: JSON.stringify({ params }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategy"] }),
  });
}

// ────────────── Today: screening / portfolio / signals ──────────────

export function useScreeningToday() {
  return useQuery({
    queryKey: ["screening-today"],
    queryFn: () => api<ScreeningToday>("/api/screening/today"),
    refetchInterval: 5_000,
  });
}

export function usePortfolio() {
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: () => api<Portfolio>("/api/portfolio"),
    refetchInterval: 5_000,
  });
}

export function useSignalsToday() {
  return useQuery({
    queryKey: ["signals-today"],
    queryFn: () => api<SignalsToday>("/api/signals/today"),
    refetchInterval: 5_000,
  });
}

// ────────────── Sync historical ──────────────

export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync-historical-status"],
    queryFn: () => api<SyncStatusResponse>("/api/sync/historical/status"),
    refetchInterval: 10_000,
  });
}

export interface SyncTriggerVariables {
  from_date: string;
  to_date: string;
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation<SyncTriggerResult, Error, SyncTriggerVariables>({
    mutationFn: ({ from_date, to_date }) =>
      api<SyncTriggerResult>(
        `/api/sync/historical/trigger?from_date=${from_date}&to_date=${to_date}`,
        { method: "POST" },
      ),
    onSuccess: (data) => {
      qc.setQueryData(["sync-historical-status"], data);
      qc.invalidateQueries({ queryKey: ["sync-historical-status"] });
    },
  });
}

// ────────────── Backtest ──────────────

export function useStartBacktest() {
  return useMutation({
    mutationFn: ({ start, end }: { start: string; end: string }) =>
      api<{ task_id: string; status: string }>("/api/backtest", {
        method: "POST",
        body: JSON.stringify({ start, end }),
      }),
  });
}

export function useBacktestTask(taskId: string | null) {
  return useQuery({
    queryKey: ["backtest-task", taskId],
    queryFn: () =>
      api<BacktestTask>(`/api/backtest/${encodeURIComponent(taskId!)}`),
    enabled: !!taskId,
    refetchInterval: (q) => {
      const status = (q.state.data as BacktestTask | undefined)?.status;
      return status === "completed" || status === "failed" ? false : 2_000;
    },
  });
}

// ────────────── Market data ──────────────

export function useMarketList() {
  return useQuery({
    queryKey: ["market-list"],
    queryFn: () => api<MarketListResponse>("/api/market/list"),
  });
}

export function useMarketHistory(
  code: string | null,
  start: string,
  end: string,
  fields?: string[],
) {
  return useQuery({
    queryKey: ["market-history", code, start, end, fields],
    queryFn: () => {
      const params = new URLSearchParams({
        code: code!,
        start,
        end,
      });
      if (fields?.length) params.set("fields", fields.join(","));
      return api<MarketHistoryResponse>(
        `/api/market/history?${params.toString()}`,
      );
    },
    enabled: !!code,
  });
}

// ────────────── Data source / dynamic pool ──────────────

export function useHealthStats() {
  return useQuery({
    queryKey: ["health-stats"],
    queryFn: () => api<DataSourceStats>("/api/health?stats=1"),
    refetchInterval: 5_000,
  });
}

export function useDynamicPool() {
  return useQuery({
    queryKey: ["dynamic-pool"],
    queryFn: () => api<DynamicPoolEntry[]>("/api/configs/pool/dynamic"),
  });
}

export function useSyncDynamicPool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<DynamicPoolSyncResult>("/api/configs/pool/dynamic/sync", {
        method: "POST",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dynamic-pool"] }),
  });
}

export function useToggleDynamicEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, isEnabled }: { code: string; isEnabled: boolean }) =>
      api<DynamicPoolEntry>(
        `/api/configs/pool/dynamic/${encodeURIComponent(code)}`,
        {
          method: "PATCH",
          body: JSON.stringify({ is_enabled: isEnabled }),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dynamic-pool"] }),
  });
}

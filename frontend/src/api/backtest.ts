import { apiGet, apiPost } from "@/api/client";

export type RebalanceFreq = "monthly" | "quarterly";

export interface BacktestRequest {
  etf_pool: string[];
  start: string;
  end: string;
  initial_cash: string;
  lookback: number;
  skip: number;
  top_n: number;
  rebalance_freq: RebalanceFreq;
}

export type MetricValue = string | number | null | undefined;

export interface BacktestMetrics {
  total_return?: MetricValue;
  annualized_return?: MetricValue;
  max_drawdown?: MetricValue;
  sharpe_ratio?: MetricValue;
  sortino_ratio?: MetricValue;
  calmar_ratio?: MetricValue;
  [key: string]: MetricValue;
}

export interface BacktestRun {
  id: number;
  name: string | null;
  etf_pool: string[];
  momentum_window: number;
  rebalance_freq: RebalanceFreq;
  start_date: string;
  end_date: string;
  metrics: BacktestMetrics | null;
  created_at: string;
}

export interface NavPoint {
  date: string;
  nav: string;
}

export interface BacktestNavResponse {
  id: number;
  nav_series: NavPoint[];
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestRun> {
  return apiPost<BacktestRun, BacktestRequest>("/api/v1/backtest", req);
}

export function getBacktestRun(id: number): Promise<BacktestRun> {
  return apiGet<BacktestRun>(`/api/v1/backtest/${id}`);
}

export function getBacktestNav(id: number): Promise<BacktestNavResponse> {
  return apiGet<BacktestNavResponse>(`/api/v1/backtest/${id}/nav`);
}

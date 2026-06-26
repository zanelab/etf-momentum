import { apiGet } from "@/api/client";

export interface SignalRow {
  etf_code: string;
  momentum_score: string | null;
  rank: number | null;
  action: string;
}

export interface SignalsApiResponse {
  date: string | null;
  rows: SignalRow[];
}

export function fetchLatestSignals(): Promise<SignalsApiResponse> {
  return apiGet<SignalsApiResponse>("/api/v1/signals/latest");
}

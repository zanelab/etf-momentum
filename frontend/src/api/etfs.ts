import { apiGet } from "@/api/client";

export interface EtfItem {
  code: string;
  name: string;
  market: string;
  category: string | null;
}

export interface EtfsApiResponse {
  items: EtfItem[];
  total: number;
  limit: number;
  offset: number;
}

export function fetchAllEtfs(): Promise<EtfsApiResponse> {
  return apiGet<EtfsApiResponse>("/api/v1/etfs?limit=500");
}

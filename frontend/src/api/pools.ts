import { apiDelete, apiGet, apiPost, apiPut } from "@/api/client";

export interface EtfPoolMember {
  code: string;
  name: string;
  market: string;
  category: string | null;
  position: number;
}

export interface EtfPoolSummary {
  id: number;
  name: string;
  description: string | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface EtfPoolDetail {
  id: number;
  name: string;
  description: string | null;
  members: EtfPoolMember[];
  created_at: string;
  updated_at: string;
}

export interface EtfPoolCreateRequest {
  name: string;
  description?: string | null;
  etf_codes: string[];
}

export type EtfPoolUpdateRequest = EtfPoolCreateRequest;

export interface EtfPoolListResponse {
  items: EtfPoolSummary[];
  total: number;
}

export function listPools(): Promise<EtfPoolListResponse> {
  return apiGet<EtfPoolListResponse>("/api/v1/pools");
}

export function getPool(id: number): Promise<EtfPoolDetail> {
  return apiGet<EtfPoolDetail>(`/api/v1/pools/${id}`);
}

export function createPool(req: EtfPoolCreateRequest): Promise<EtfPoolDetail> {
  return apiPost<EtfPoolDetail, EtfPoolCreateRequest>("/api/v1/pools", req);
}

export function updatePool(
  id: number,
  req: EtfPoolUpdateRequest,
): Promise<EtfPoolDetail> {
  return apiPut<EtfPoolDetail, EtfPoolUpdateRequest>(
    `/api/v1/pools/${id}`,
    req,
  );
}

export function deletePool(id: number): Promise<void> {
  return apiDelete<void>(`/api/v1/pools/${id}`);
}

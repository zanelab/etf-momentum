import { create } from "zustand";

export type HealthStatus = "idle" | "loading" | "ok" | "error";

export interface HealthData {
  status: string;
}

export interface HealthState {
  status: HealthStatus;
  data: HealthData | null;
  error: string | null;
  setLoading: () => void;
  setOk: (data: HealthData) => void;
  setError: (message: string) => void;
  reset: () => void;
}

const initialState = {
  status: "idle" as HealthStatus,
  data: null,
  error: null,
};

export const useHealthStore = create<HealthState>((set) => ({
  ...initialState,
  setLoading: () => set({ status: "loading", error: null }),
  setOk: (data) => set({ status: "ok", data, error: null }),
  setError: (message) => set({ status: "error", error: message, data: null }),
  reset: () => set(initialState),
}));

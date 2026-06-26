import { create } from "zustand";

import { fetchLatestSignals, type SignalRow, type SignalsApiResponse } from "@/api/signals";

export type AsyncStatus = "idle" | "loading" | "ok" | "error";

export interface SignalsState {
  status: AsyncStatus;
  data: SignalsApiResponse | null;
  error: string | null;
  fetchLatest: () => Promise<void>;
  reset: () => void;
}

const initialState = {
  status: "idle" as AsyncStatus,
  data: null as SignalsApiResponse | null,
  error: null as string | null,
};

export const useSignalsStore = create<SignalsState>((set) => ({
  ...initialState,
  fetchLatest: async () => {
    set({ status: "loading", error: null });
    try {
      const data = await fetchLatestSignals();
      set({ status: "ok", data, error: null });
    } catch (err) {
      set({ status: "error", error: err instanceof Error ? err.message : String(err), data: null });
    }
  },
  reset: () => set(initialState),
}));

export type { SignalRow };

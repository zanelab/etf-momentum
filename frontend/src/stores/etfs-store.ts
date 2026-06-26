import { create } from "zustand";

import { fetchAllEtfs, type EtfItem, type EtfsApiResponse } from "@/api/etfs";

export type AsyncStatus = "idle" | "loading" | "ok" | "error";

export interface EtfsState {
  status: AsyncStatus;
  data: EtfsApiResponse | null;
  error: string | null;
  fetchAll: () => Promise<void>;
  reset: () => void;
}

const initialState = {
  status: "idle" as AsyncStatus,
  data: null as EtfsApiResponse | null,
  error: null as string | null,
};

export const useEtfsStore = create<EtfsState>((set) => ({
  ...initialState,
  fetchAll: async () => {
    set({ status: "loading", error: null });
    try {
      const data = await fetchAllEtfs();
      set({ status: "ok", data, error: null });
    } catch (err) {
      set({ status: "error", error: err instanceof Error ? err.message : String(err), data: null });
    }
  },
  reset: () => set(initialState),
}));

export type { EtfItem };

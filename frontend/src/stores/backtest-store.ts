import { create } from "zustand";

import {
  getBacktestNav,
  runBacktest,
  type BacktestNavResponse,
  type BacktestRequest,
  type BacktestRun,
  type NavPoint,
} from "@/api/backtest";
import { ApiError } from "@/api/client";

export type AsyncStatus = "idle" | "loading" | "ok" | "error";

export type FormErrors = Record<string, string>;

interface FastApiViolation {
  loc?: unknown;
  msg?: unknown;
  type?: unknown;
}

function isFastApiViolation(value: unknown): value is FastApiViolation {
  return typeof value === "object" && value !== null;
}

function extractFieldErrors(detail: unknown): FormErrors {
  if (!Array.isArray(detail)) {
    return {};
  }
  const errors: FormErrors = {};
  for (const item of detail) {
    if (!isFastApiViolation(item)) continue;
    const loc = Array.isArray(item.loc) ? item.loc : [];
    const msg = typeof item.msg === "string" ? item.msg : null;
    if (!msg) continue;
    const stringSegments = loc.filter(
      (segment): segment is string => typeof segment === "string",
    );
    const field = stringSegments[stringSegments.length - 1] ?? "form";
    errors[field] = msg;
  }
  return errors;
}

export interface BacktestState {
  submitStatus: AsyncStatus;
  navStatus: AsyncStatus;
  currentRun: BacktestRun | null;
  navSeries: NavPoint[];
  formErrors: FormErrors;
  submitError: string | null;
  navError: string | null;
  submit: (req: BacktestRequest) => Promise<void>;
  fetchNav: (id: number) => Promise<void>;
  reset: () => void;
}

const initialState = {
  submitStatus: "idle" as AsyncStatus,
  navStatus: "idle" as AsyncStatus,
  currentRun: null as BacktestRun | null,
  navSeries: [] as NavPoint[],
  formErrors: {} as FormErrors,
  submitError: null as string | null,
  navError: null as string | null,
};

export const useBacktestStore = create<BacktestState>((set, get) => ({
  ...initialState,
  submit: async (req) => {
    set({
      submitStatus: "loading",
      formErrors: {},
      submitError: null,
      navStatus: "idle",
      navSeries: [],
      navError: null,
    });
    try {
      const run = await runBacktest(req);
      set({ submitStatus: "ok", currentRun: run });
      await get().fetchNav(run.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        set({
          submitStatus: "error",
          formErrors: extractFieldErrors(err.detail),
          submitError: err.message,
        });
        return;
      }
      const message = err instanceof Error ? err.message : String(err);
      set({
        submitStatus: "error",
        submitError: message,
        formErrors: {},
      });
    }
  },
  fetchNav: async (id) => {
    set({ navStatus: "loading", navError: null });
    try {
      const response: BacktestNavResponse = await getBacktestNav(id);
      set({ navStatus: "ok", navSeries: response.nav_series, navError: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ navStatus: "error", navError: message });
    }
  },
  reset: () => set(initialState),
}));

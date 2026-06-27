import { create } from "zustand";

import {
  createPool,
  deletePool,
  getPool,
  listPools,
  updatePool,
  type EtfPoolCreateRequest,
  type EtfPoolDetail,
  type EtfPoolSummary,
  type EtfPoolUpdateRequest,
} from "@/api/pools";
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

function deriveFieldFromMessage(message: string): FormErrors {
  const lower = message.toLowerCase();
  if (lower.includes("name") || lower.includes("已存在") || lower.includes("exists")) {
    return { name: message };
  }
  if (lower.includes("etf") || lower.includes("code")) {
    return { etf_codes: message };
  }
  return {};
}

export interface PoolsState {
  status: AsyncStatus;
  items: EtfPoolSummary[];
  currentPool: EtfPoolDetail | null;
  currentPoolStatus: AsyncStatus;
  createStatus: AsyncStatus;
  updateStatus: AsyncStatus;
  deleteStatus: AsyncStatus;
  error: string | null;
  formErrors: FormErrors;
  createError: string | null;
  updateError: string | null;
  deleteError: string | null;
  fetchAll: () => Promise<void>;
  fetchOne: (id: number) => Promise<void>;
  create: (req: EtfPoolCreateRequest) => Promise<EtfPoolDetail | null>;
  update: (id: number, req: EtfPoolUpdateRequest) => Promise<EtfPoolDetail | null>;
  remove: (id: number) => Promise<boolean>;
  reset: () => void;
  clearFormErrors: () => void;
}

const initialState = {
  status: "idle" as AsyncStatus,
  items: [] as EtfPoolSummary[],
  currentPool: null as EtfPoolDetail | null,
  currentPoolStatus: "idle" as AsyncStatus,
  createStatus: "idle" as AsyncStatus,
  updateStatus: "idle" as AsyncStatus,
  deleteStatus: "idle" as AsyncStatus,
  error: null as string | null,
  formErrors: {} as FormErrors,
  createError: null as string | null,
  updateError: null as string | null,
  deleteError: null as string | null,
};

export const usePoolsStore = create<PoolsState>((set) => ({
  ...initialState,
  fetchAll: async () => {
    set({ status: "loading", error: null });
    try {
      const response = await listPools();
      set({ status: "ok", items: response.items, error: null });
    } catch (err) {
      set({
        status: "error",
        error: err instanceof Error ? err.message : String(err),
        items: [],
      });
    }
  },
  fetchOne: async (id) => {
    set({ currentPoolStatus: "loading", error: null });
    try {
      const detail = await getPool(id);
      set({ currentPoolStatus: "ok", currentPool: detail, error: null });
    } catch (err) {
      set({
        currentPoolStatus: "error",
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },
  create: async (req) => {
    set({
      createStatus: "loading",
      createError: null,
      formErrors: {},
    });
    try {
      const detail = await createPool(req);
      set((state) => ({
        createStatus: "ok",
        currentPool: detail,
        items: [
          ...state.items,
          {
            id: detail.id,
            name: detail.name,
            description: detail.description,
            member_count: detail.members.length,
            created_at: detail.created_at,
            updated_at: detail.updated_at,
          },
        ],
      }));
      return detail;
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 422) {
          set({
            createStatus: "error",
            formErrors: extractFieldErrors(err.detail),
            createError: err.message,
          });
          return null;
        }
        if (err.status === 409) {
          set({
            createStatus: "error",
            formErrors: deriveFieldFromMessage(err.message),
            createError: err.message,
          });
          return null;
        }
      }
      const message = err instanceof Error ? err.message : String(err);
      set({ createStatus: "error", createError: message });
      return null;
    }
  },
  update: async (id, req) => {
    set({
      updateStatus: "loading",
      updateError: null,
      formErrors: {},
    });
    try {
      const detail = await updatePool(id, req);
      set((state) => ({
        updateStatus: "ok",
        currentPool: detail,
        items: state.items.map((item) =>
          item.id === detail.id
            ? {
                ...item,
                name: detail.name,
                description: detail.description,
                member_count: detail.members.length,
                updated_at: detail.updated_at,
              }
            : item,
        ),
      }));
      return detail;
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 422) {
          set({
            updateStatus: "error",
            formErrors: extractFieldErrors(err.detail),
            updateError: err.message,
          });
          return null;
        }
        if (err.status === 409) {
          set({
            updateStatus: "error",
            formErrors: deriveFieldFromMessage(err.message),
            updateError: err.message,
          });
          return null;
        }
        if (err.status === 404) {
          set({
            updateStatus: "error",
            updateError: err.message,
          });
          set((state) => ({ items: state.items.filter((item) => item.id !== id) }));
          return null;
        }
      }
      const message = err instanceof Error ? err.message : String(err);
      set({ updateStatus: "error", updateError: message });
      return null;
    }
  },
  remove: async (id) => {
    set({ deleteStatus: "loading", deleteError: null });
    try {
      await deletePool(id);
      set((state) => ({
        deleteStatus: "ok",
        items: state.items.filter((item) => item.id !== id),
        currentPool: state.currentPool?.id === id ? null : state.currentPool,
      }));
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ deleteStatus: "error", deleteError: message });
      return false;
    }
  },
  reset: () => set(initialState),
  clearFormErrors: () => set({ formErrors: {} }),
}));

export type { EtfPoolDetail, EtfPoolSummary };

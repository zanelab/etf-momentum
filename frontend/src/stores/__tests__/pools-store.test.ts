import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import * as poolsApi from "@/api/pools";
import { usePoolsStore } from "@/stores/pools-store";

const SAMPLE_SUMMARY = {
  id: 1,
  name: "宽基核心",
  description: "沪深300+中证500",
  member_count: 2,
  created_at: "2026-06-27T00:00:00",
  updated_at: "2026-06-27T00:00:00",
};

const SAMPLE_DETAIL = {
  id: 1,
  name: "宽基核心",
  description: "沪深300+中证500",
  members: [
    {
      code: "510300",
      name: "沪深300ETF",
      market: "SH",
      category: "宽基",
      position: 0,
    },
    {
      code: "510500",
      name: "中证500ETF",
      market: "SH",
      category: "宽基",
      position: 1,
    },
  ],
  created_at: "2026-06-27T00:00:00",
  updated_at: "2026-06-27T00:00:00",
};

const SAMPLE_REQUEST = {
  name: "宽基核心",
  description: "沪深300+中证500",
  etf_codes: ["510300", "510500"],
};

function makeApiError(status: number, detail: unknown, message?: string) {
  const msg =
    message ??
    (typeof detail === "string" ? detail : `${status} ${status === 409 ? "Conflict" : "Bad Request"}`);
  return new ApiError(msg, status, detail);
}

describe("usePoolsStore", () => {
  beforeEach(() => {
    usePoolsStore.getState().reset();
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("starts idle with empty items", () => {
      const state = usePoolsStore.getState();
      expect(state.status).toBe("idle");
      expect(state.items).toEqual([]);
      expect(state.currentPool).toBeNull();
      expect(state.error).toBeNull();
      expect(state.formErrors).toEqual({});
    });
  });

  describe("fetchAll", () => {
    it("transitions to ok with items", async () => {
      vi.spyOn(poolsApi, "listPools").mockResolvedValue({
        items: [SAMPLE_SUMMARY],
        total: 1,
      });

      await usePoolsStore.getState().fetchAll();

      const state = usePoolsStore.getState();
      expect(state.status).toBe("ok");
      expect(state.items).toEqual([SAMPLE_SUMMARY]);
      expect(state.error).toBeNull();
    });

    it("transitions to error and clears items", async () => {
      vi.spyOn(poolsApi, "listPools").mockRejectedValue(new Error("network"));

      await usePoolsStore.getState().fetchAll();

      const state = usePoolsStore.getState();
      expect(state.status).toBe("error");
      expect(state.error).toBe("network");
      expect(state.items).toEqual([]);
    });
  });

  describe("fetchOne", () => {
    it("transitions to ok with detail", async () => {
      vi.spyOn(poolsApi, "getPool").mockResolvedValue(SAMPLE_DETAIL);

      await usePoolsStore.getState().fetchOne(1);

      const state = usePoolsStore.getState();
      expect(state.currentPoolStatus).toBe("ok");
      expect(state.currentPool).toEqual(SAMPLE_DETAIL);
    });

    it("surfaces 404 in error", async () => {
      vi.spyOn(poolsApi, "getPool").mockRejectedValue(
        makeApiError(404, "EtfPool 999 not found"),
      );

      await usePoolsStore.getState().fetchOne(999);

      const state = usePoolsStore.getState();
      expect(state.currentPoolStatus).toBe("error");
      expect(state.error).toBe("EtfPool 999 not found");
    });
  });

  describe("create", () => {
    it("returns detail and appends summary on success", async () => {
      vi.spyOn(poolsApi, "createPool").mockResolvedValue(SAMPLE_DETAIL);

      const result = await usePoolsStore.getState().create(SAMPLE_REQUEST);

      expect(result).toEqual(SAMPLE_DETAIL);
      const state = usePoolsStore.getState();
      expect(state.createStatus).toBe("ok");
      expect(state.currentPool).toEqual(SAMPLE_DETAIL);
      expect(state.items).toHaveLength(1);
      expect(state.items[0]?.id).toBe(1);
    });

    it("maps 422 violations to formErrors keyed by field", async () => {
      vi.spyOn(poolsApi, "createPool").mockRejectedValue(
        makeApiError(
          422,
          [{ loc: ["body", "etf_codes"], msg: "Unknown ETF codes: ['999999']", type: "value_error" }],
          "Unknown ETF codes: ['999999']",
        ),
      );

      const result = await usePoolsStore.getState().create({
        ...SAMPLE_REQUEST,
        etf_codes: ["999999"],
      });

      expect(result).toBeNull();
      const state = usePoolsStore.getState();
      expect(state.createStatus).toBe("error");
      expect(state.formErrors.etf_codes).toContain("999999");
      expect(state.createError).toContain("999999");
    });

    it("maps 409 to name formError", async () => {
      vi.spyOn(poolsApi, "createPool").mockRejectedValue(
        makeApiError(409, "Pool '宽基核心' already exists"),
      );

      const result = await usePoolsStore.getState().create(SAMPLE_REQUEST);

      expect(result).toBeNull();
      const state = usePoolsStore.getState();
      expect(state.createStatus).toBe("error");
      expect(state.formErrors.name).toContain("already exists");
      expect(state.createError).toContain("already exists");
    });
  });

  describe("update", () => {
    beforeEach(async () => {
      vi.spyOn(poolsApi, "listPools").mockResolvedValue({
        items: [SAMPLE_SUMMARY],
        total: 1,
      });
      await usePoolsStore.getState().fetchAll();
    });

    it("updates currentPool and patches summary in items", async () => {
      const updatedDetail = {
        ...SAMPLE_DETAIL,
        name: "宽基核心 2",
        members: [
          ...SAMPLE_DETAIL.members,
          {
            code: "510330",
            name: "沪深300ETF基金",
            market: "SH",
            category: "宽基",
            position: 2,
          },
        ],
        updated_at: "2026-06-28T00:00:00",
      };
      vi.spyOn(poolsApi, "updatePool").mockResolvedValue(updatedDetail);

      const result = await usePoolsStore.getState().update(1, {
        ...SAMPLE_REQUEST,
        name: "宽基核心 2",
        etf_codes: ["510300", "510500", "510330"],
      });

      expect(result).toEqual(updatedDetail);
      const state = usePoolsStore.getState();
      expect(state.updateStatus).toBe("ok");
      expect(state.currentPool?.name).toBe("宽基核心 2");
      expect(state.items[0]?.name).toBe("宽基核心 2");
      expect(state.items[0]?.member_count).toBe(3);
    });

    it("maps 409 rename collision to name formError", async () => {
      vi.spyOn(poolsApi, "updatePool").mockRejectedValue(
        makeApiError(409, "Pool 'x' already exists"),
      );

      const result = await usePoolsStore.getState().update(1, SAMPLE_REQUEST);

      expect(result).toBeNull();
      const state = usePoolsStore.getState();
      expect(state.updateStatus).toBe("error");
      expect(state.formErrors.name).toContain("already exists");
    });

    it("drops the pool from items on 404", async () => {
      vi.spyOn(poolsApi, "updatePool").mockRejectedValue(
        makeApiError(404, "EtfPool 1 not found"),
      );

      const result = await usePoolsStore.getState().update(1, SAMPLE_REQUEST);

      expect(result).toBeNull();
      const state = usePoolsStore.getState();
      expect(state.updateStatus).toBe("error");
      expect(state.items).toEqual([]);
    });
  });

  describe("remove", () => {
    beforeEach(async () => {
      vi.spyOn(poolsApi, "listPools").mockResolvedValue({
        items: [SAMPLE_SUMMARY],
        total: 1,
      });
      await usePoolsStore.getState().fetchAll();
    });

    it("removes the pool from items on success", async () => {
      vi.spyOn(poolsApi, "deletePool").mockResolvedValue(undefined);

      const ok = await usePoolsStore.getState().remove(1);

      expect(ok).toBe(true);
      const state = usePoolsStore.getState();
      expect(state.deleteStatus).toBe("ok");
      expect(state.items).toEqual([]);
    });

    it("clears currentPool when the deleted pool was selected", async () => {
      vi.spyOn(poolsApi, "getPool").mockResolvedValue(SAMPLE_DETAIL);
      await usePoolsStore.getState().fetchOne(1);
      vi.spyOn(poolsApi, "deletePool").mockResolvedValue(undefined);

      await usePoolsStore.getState().remove(1);

      const state = usePoolsStore.getState();
      expect(state.currentPool).toBeNull();
    });

    it("keeps items intact on failure", async () => {
      vi.spyOn(poolsApi, "deletePool").mockRejectedValue(
        makeApiError(500, "boom"),
      );

      const ok = await usePoolsStore.getState().remove(1);

      expect(ok).toBe(false);
      const state = usePoolsStore.getState();
      expect(state.deleteStatus).toBe("error");
      expect(state.deleteError).toBe("boom");
      expect(state.items).toHaveLength(1);
    });
  });

  describe("reset", () => {
    it("clears all state including formErrors", async () => {
      vi.spyOn(poolsApi, "createPool").mockRejectedValue(
        makeApiError(409, "Pool 'x' already exists"),
      );
      await usePoolsStore.getState().create(SAMPLE_REQUEST);

      usePoolsStore.getState().reset();

      const state = usePoolsStore.getState();
      expect(state.status).toBe("idle");
      expect(state.items).toEqual([]);
      expect(state.formErrors).toEqual({});
      expect(state.createStatus).toBe("idle");
    });
  });

  describe("clearFormErrors", () => {
    it("clears only formErrors", async () => {
      vi.spyOn(poolsApi, "createPool").mockRejectedValue(
        makeApiError(409, "Pool 'x' already exists"),
      );
      await usePoolsStore.getState().create(SAMPLE_REQUEST);

      usePoolsStore.getState().clearFormErrors();

      const state = usePoolsStore.getState();
      expect(state.formErrors).toEqual({});
      expect(state.createError).toBe("Pool 'x' already exists");
    });
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";

import * as etfsApi from "@/api/etfs";
import { useEtfsStore } from "@/stores/etfs-store";

describe("useEtfsStore", () => {
  beforeEach(() => {
    useEtfsStore.getState().reset();
    vi.restoreAllMocks();
  });

  it("starts in idle state", () => {
    const state = useEtfsStore.getState();
    expect(state.status).toBe("idle");
    expect(state.data).toBeNull();
    expect(state.error).toBeNull();
  });

  it("transitions to ok with payload", async () => {
    const payload = {
      items: [{ code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" }],
      total: 1,
      limit: 500,
      offset: 0,
    };
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue(payload);

    await useEtfsStore.getState().fetchAll();

    const state = useEtfsStore.getState();
    expect(state.status).toBe("ok");
    expect(state.data).toEqual(payload);
    expect(state.error).toBeNull();
  });

  it("transitions to error and clears data on failure", async () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockRejectedValue(new Error("etfs 502"));

    await useEtfsStore.getState().fetchAll();

    const state = useEtfsStore.getState();
    expect(state.status).toBe("error");
    expect(state.error).toBe("etfs 502");
    expect(state.data).toBeNull();
  });

  it("reset clears all state", async () => {
    vi.spyOn(etfsApi, "fetchAllEtfs").mockResolvedValue({
      items: [],
      total: 0,
      limit: 500,
      offset: 0,
    });
    await useEtfsStore.getState().fetchAll();
    useEtfsStore.getState().reset();
    const state = useEtfsStore.getState();
    expect(state.status).toBe("idle");
    expect(state.data).toBeNull();
  });
});

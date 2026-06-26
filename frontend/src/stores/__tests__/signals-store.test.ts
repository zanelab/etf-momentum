import { beforeEach, describe, expect, it, vi } from "vitest";

import * as signalsApi from "@/api/signals";
import { useSignalsStore } from "@/stores/signals-store";

describe("useSignalsStore", () => {
  beforeEach(() => {
    useSignalsStore.getState().reset();
    vi.restoreAllMocks();
  });

  it("starts in idle state with null data and error", () => {
    const state = useSignalsStore.getState();
    expect(state.status).toBe("idle");
    expect(state.data).toBeNull();
    expect(state.error).toBeNull();
  });

  it("transitions idle → loading → ok on successful fetch", async () => {
    const payload = {
      date: "2026-06-26",
      rows: [{ etf_code: "510300", momentum_score: "0.1", rank: 1, action: "BUY" }],
    };
    vi.spyOn(signalsApi, "fetchLatestSignals").mockResolvedValue(payload);

    await useSignalsStore.getState().fetchLatest();

    const state = useSignalsStore.getState();
    expect(state.status).toBe("ok");
    expect(state.data).toEqual(payload);
    expect(state.error).toBeNull();
  });

  it("transitions idle → loading → error on failed fetch", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals").mockRejectedValue(new Error("network"));

    await useSignalsStore.getState().fetchLatest();

    const state = useSignalsStore.getState();
    expect(state.status).toBe("error");
    expect(state.error).toBe("network");
    expect(state.data).toBeNull();
  });

  it("clears error when starting a new fetch", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals")
      .mockRejectedValueOnce(new Error("first"))
      .mockResolvedValueOnce({ date: "2026-06-26", rows: [] });

    await useSignalsStore.getState().fetchLatest();
    expect(useSignalsStore.getState().status).toBe("error");

    await useSignalsStore.getState().fetchLatest();
    const state = useSignalsStore.getState();
    expect(state.status).toBe("ok");
    expect(state.error).toBeNull();
  });

  it("reset returns to initial state", async () => {
    vi.spyOn(signalsApi, "fetchLatestSignals").mockResolvedValue({ date: "2026-06-26", rows: [] });
    await useSignalsStore.getState().fetchLatest();
    useSignalsStore.getState().reset();
    const state = useSignalsStore.getState();
    expect(state.status).toBe("idle");
    expect(state.data).toBeNull();
  });
});

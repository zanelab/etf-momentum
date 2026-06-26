import { beforeEach, describe, expect, it } from "vitest";

import { useHealthStore } from "@/stores/health-store";

describe("useHealthStore", () => {
  beforeEach(() => {
    useHealthStore.getState().reset();
  });

  it("starts with idle status", () => {
    expect(useHealthStore.getState().status).toBe("idle");
    expect(useHealthStore.getState().data).toBeNull();
    expect(useHealthStore.getState().error).toBeNull();
  });

  it("transitions to loading", () => {
    useHealthStore.getState().setLoading();
    const state = useHealthStore.getState();
    expect(state.status).toBe("loading");
    expect(state.error).toBeNull();
  });

  it("transitions to ok with payload", () => {
    useHealthStore.getState().setOk({ status: "ok" });
    const state = useHealthStore.getState();
    expect(state.status).toBe("ok");
    expect(state.data).toEqual({ status: "ok" });
    expect(state.error).toBeNull();
  });

  it("transitions to error with message", () => {
    useHealthStore.getState().setError("network down");
    const state = useHealthStore.getState();
    expect(state.status).toBe("error");
    expect(state.error).toBe("network down");
    expect(state.data).toBeNull();
  });

  it("resets to idle", () => {
    useHealthStore.getState().setOk({ status: "ok" });
    useHealthStore.getState().reset();
    const state = useHealthStore.getState();
    expect(state.status).toBe("idle");
    expect(state.data).toBeNull();
    expect(state.error).toBeNull();
  });
});

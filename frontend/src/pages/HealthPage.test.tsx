import * as apiClient from "@/api/client";
import { HealthPage } from "@/pages/HealthPage";
import { useHealthStore } from "@/stores/health-store";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("HealthPage", () => {
  beforeEach(() => {
    useHealthStore.getState().reset();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the section heading and description", () => {
    vi.spyOn(apiClient, "apiGet").mockResolvedValue({ status: "ok" });
    render(<HealthPage />);
    expect(screen.getByRole("heading", { name: "后端健康检查" })).toBeInTheDocument();
  });

  it("triggers apiGet('/health') exactly once on mount", async () => {
    const spy = vi.spyOn(apiClient, "apiGet").mockResolvedValue({ status: "ok" });
    render(<HealthPage />);
    await vi.waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    expect(spy).toHaveBeenCalledWith("/health");
  });

  it("transitions store to ok after a successful apiGet", async () => {
    vi.spyOn(apiClient, "apiGet").mockResolvedValue({ status: "ok" });
    render(<HealthPage />);
    await vi.waitFor(() => expect(useHealthStore.getState().status).toBe("ok"));
    expect(useHealthStore.getState().data).toEqual({ status: "ok" });
    expect(useHealthStore.getState().error).toBeNull();
  });

  it("transitions store to error after a failed apiGet", async () => {
    vi.spyOn(apiClient, "apiGet").mockRejectedValue(new Error("502 Bad Gateway"));
    render(<HealthPage />);
    await vi.waitFor(() => expect(useHealthStore.getState().status).toBe("error"));
    expect(useHealthStore.getState().error).toBe("502 Bad Gateway");
  });

  it("shows the retry button (重新检测) when status is ok", async () => {
    vi.spyOn(apiClient, "apiGet").mockResolvedValue({ status: "ok" });
    render(<HealthPage />);
    await vi.waitFor(() => expect(useHealthStore.getState().status).toBe("ok"));
    const btn = screen.getByRole("button", { name: "重新检测" });
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
  });

  it("shows '检测中...' and disables the button while loading", async () => {
    // Make apiGet never resolve so the page stays in loading state.
    vi.spyOn(apiClient, "apiGet").mockReturnValue(new Promise(() => {}));
    render(<HealthPage />);
    await vi.waitFor(() => expect(useHealthStore.getState().status).toBe("loading"));
    const btn = screen.getByRole("button", { name: "检测中..." });
    expect(btn).toBeInTheDocument();
    expect(btn).toBeDisabled();
  });

  it("renders the JSON data in a <pre> block when status is ok", async () => {
    vi.spyOn(apiClient, "apiGet").mockResolvedValue({ status: "ok" });
    const { container } = render(<HealthPage />);
    await vi.waitFor(() => expect(useHealthStore.getState().status).toBe("ok"));
    const pre = container.querySelector("pre");
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toContain('"status"');
    expect(pre?.textContent).toContain('"ok"');
  });

  it("renders the error message in a destructive-styled container when status is error", async () => {
    vi.spyOn(apiClient, "apiGet").mockRejectedValue(new Error("network down"));
    render(<HealthPage />);
    await vi.waitFor(() => expect(useHealthStore.getState().status).toBe("error"));
    expect(screen.getByText("network down")).toBeInTheDocument();
  });

  it("does not show a <pre> block or error text while loading", () => {
    // apiGet never resolves → page stuck in loading state
    vi.spyOn(apiClient, "apiGet").mockReturnValue(new Promise(() => {}));
    const { container } = render(<HealthPage />);
    expect(container.querySelector("pre")).toBeNull();
    expect(screen.queryByText("network down")).toBeNull();
  });

  it("triggers another apiGet when the retry button is clicked", async () => {
    const spy = vi.spyOn(apiClient, "apiGet").mockResolvedValue({ status: "ok" });
    render(<HealthPage />);
    // Wait until the page finishes its first check (status=ok → button re-enabled).
    await vi.waitFor(() =>
      expect(useHealthStore.getState().status).toBe("ok"),
    );
    expect(spy).toHaveBeenCalledTimes(1);
    const btn = screen.getByRole("button", { name: "重新检测" });
    btn.click();
    await vi.waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
  });
});
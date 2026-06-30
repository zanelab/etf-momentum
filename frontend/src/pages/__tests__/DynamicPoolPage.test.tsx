import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DynamicPoolPage from "@/pages/DynamicPoolPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Default body for /api/sync/historical/status — a single dynamic-pool entry.
const defaultEtfEntry = {
  code: "510300.XSHG",
  name: "沪深300ETF",
  last_synced_date: null,
  last_synced_at: "2026-01-15T10:00:00Z",
  is_enabled: true,
  status: "ok" as const,
  error: null,
  progress: null,
};

function defaultStatusBody(overrides: Record<string, unknown> = {}) {
  return {
    as_of: "2026-01-15",
    etfs: [defaultEtfEntry],
    in_progress: null,
    is_running: false,
    ...overrides,
  };
}

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
        // Allow a function value to control response timing/contents
        // (useful for never-resolving or delayed mutation responses).
        if (typeof value === "function") {
          return await (value as () => Promise<Response> | Response)();
        }
        return new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 404 });
  }) as unknown as typeof fetch;
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <DynamicPoolPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("DynamicPoolPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();
  });
  afterEach(() => vi.restoreAllMocks());

  it("renders the dynamic pool heading", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody(),
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/动态池/)).toBeInTheDocument());
  });

  it("renders an empty state when no rows", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody({ as_of: null, etfs: [] }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/暂无动态池条目/)).toBeInTheDocument());
  });

  it("renders two sync buttons", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody(),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeInTheDocument();
  });

  it("second button is disabled when pool is empty", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody({ as_of: null, etfs: [] }),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeDisabled();
    });
    expect(screen.getByRole("button", { name: "同步 ETF" })).not.toBeDisabled();
  });

  it("row click navigates to /dynamic-pool/:code", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody(),
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    fireEvent.click(row);
    expect(mockNavigate).toHaveBeenCalledWith("/dynamic-pool/510300.XSHG");
  });

  it("checkbox click does NOT navigate", async () => {
    // The toggle PATCH endpoint still targets the dynamic-pool-config path.
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody(),
      "/api/configs/pool/dynamic/510300.XSHG": {
        code: "510300.XSHG", name: "沪深300ETF",
        is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z",
      },
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    const checkbox = row.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox).toBeTruthy();
    await userEvent.click(checkbox);
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/configs/pool/dynamic/510300.XSHG",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

describe("DynamicPoolPage progress UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();
  });
  afterEach(() => vi.restoreAllMocks());

  it("shows top progress banner when is_running=true", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody({
        in_progress: [
          {
            code: "510300", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-20", total_days: 3, completed_days: 2,
            overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
          },
        ],
        is_running: true,
      }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sync-progress-banner")).toBeInTheDocument());
  });

  it("shows row progress bar when in_progress contains the row's code", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody({
        in_progress: [
          {
            code: "510300.XSHG", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-20", total_days: 3, completed_days: 2,
            overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
          },
        ],
        is_running: true,
      }),
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    expect(row.querySelector('[data-testid="row-progress-bar"]')).toBeTruthy();
  });

  it("disables 同步 ETF button when historyRunning (互锁)", async () => {
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody({
        in_progress: [
          {
            code: "510300.XSHG", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-20", total_days: 3, completed_days: 2,
            overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
          },
        ],
        is_running: true,
      }),
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF" })).toBeDisabled();
    });
  });

  it("opens DateRangePicker when 历史数据 button clicked; confirm triggers mutate with range", async () => {
    const user = userEvent.setup();
    setupFetchMock({
      "/api/sync/historical/status": defaultStatusBody({ in_progress: null, is_running: false }),
      "/api/sync/historical/trigger": {
        as_of: "2026-01-15",
        etfs: [],
        in_progress: null,
        is_running: false,
        synced_count: 1,
        run_at: "2026-06-29T10:00:00Z",
      },
    });
    renderPage();
    const historyBtn = await waitFor(() => screen.getByRole("button", { name: "同步 ETF 历史数据" }));
    await user.click(historyBtn);

    // Picker should open
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeInTheDocument();

    // Adjust inputs to known values and confirm
    const fromInput = screen.getByLabelText(/from/i) as HTMLInputElement;
    const toInput = screen.getByLabelText(/to/i) as HTMLInputElement;
    await user.clear(fromInput);
    await user.type(fromInput, "2024-04-19");
    await user.clear(toInput);
    await user.type(toInput, "2024-04-21");
    await user.click(screen.getByRole("button", { name: /开始同步/ }));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/sync/historical/trigger?from_date=2024-04-19&to_date=2024-04-21",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});

describe("DynamicPoolPage button state machine (M17)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();
  });
  afterEach(() => vi.restoreAllMocks());

  it("shows '同步 ETF 历史数据' label when idle", async () => {
    setupFetchMock({
      "/api/sync/historical/status": {
        as_of: null,
        etfs: [
          {
            code: "510300.XSHG", name: "沪深300ETF",
            last_synced_date: null, last_synced_at: null,
            is_enabled: true, status: "never", error: null, progress: null,
          },
        ],
        in_progress: null, is_running: false,
      },
    });
    renderPage();
    const btn = await waitFor(() =>
      screen.getByRole("button", { name: "同步 ETF 历史数据" })
    );
    expect(btn).not.toBeDisabled();
  });

  it("shows '取消' label and clickable when is_running=true", async () => {
    setupFetchMock({
      "/api/sync/historical/status": {
        as_of: null,
        etfs: [
          {
            code: "510300.XSHG", name: "沪深300ETF",
            last_synced_date: null, last_synced_at: null,
            is_enabled: true, status: "in_progress",
            error: null,
            progress: { completed: 1, total: 3, current_code: "510300.XSHG", current_date: "2024-04-19", percent: 33 },
          },
        ],
        in_progress: [
          { code: "510300.XSHG", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-19", total_days: 3, completed_days: 1,
            overall_index: 1, overall_total: 3, started_at: "2026-06-29T10:00:00Z" },
        ],
        is_running: true,
      },
      "/api/sync/historical/cancel": { cancelled: true },
    });
    renderPage();
    const btn = await waitFor(() =>
      screen.getByRole("button", { name: "取消" })
    );
    expect(btn).not.toBeDisabled();

    // Click triggers cancel
    const user = userEvent.setup();
    await user.click(btn);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/sync/historical/cancel",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("disables cancel button while cancel is in flight", async () => {
    const user = userEvent.setup();
    let resolveCancel: (() => void) | undefined;
    const cancelPromise = new Promise<void>((r) => { resolveCancel = r; });
    setupFetchMock({
      "/api/sync/historical/status": {
        as_of: null,
        etfs: [
          {
            code: "510300.XSHG", name: "沪深300ETF",
            last_synced_date: null, last_synced_at: null,
            is_enabled: true, status: "in_progress",
            error: null,
            progress: { completed: 1, total: 3, current_code: "510300.XSHG", current_date: "2024-04-19", percent: 33 },
          },
        ],
        in_progress: [
          { code: "510300.XSHG", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-19", total_days: 3, completed_days: 1,
            overall_index: 1, overall_total: 3, started_at: "2026-06-29T10:00:00Z" },
        ],
        is_running: true,
      },
      "/api/sync/historical/cancel": async () => {
        await cancelPromise;
        return new Response(JSON.stringify({ cancelled: true }), {
          status: 200, headers: { "Content-Type": "application/json" },
        });
      },
    });
    renderPage();
    const cancelBtn = await waitFor(() =>
      screen.getByRole("button", { name: "取消" })
    );
    expect(cancelBtn).not.toBeDisabled();

    await user.click(cancelBtn);

    // After click, mutation is in flight → button should be disabled.
    // The state machine switches the label to "取消中…" while
    // cancelSync.isPending && historyRunning.
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /取消中…|取消/ });
      expect(btn).toBeDisabled();
    });

    // Cleanup: resolve the pending cancel so the test exits cleanly.
    resolveCancel?.();
  });

  it("does not render standalone cancel-sync-button (合并取消)", async () => {
    setupFetchMock({
      "/api/sync/historical/status": {
        as_of: null,
        etfs: [
          {
            code: "510300.XSHG", name: "沪深300ETF",
            last_synced_date: null, last_synced_at: null,
            is_enabled: true, status: "in_progress",
            error: null,
            progress: { completed: 1, total: 3, current_code: "510300.XSHG", current_date: "2024-04-19", percent: 33 },
          },
        ],
        in_progress: [
          { code: "510300.XSHG", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-19", total_days: 3, completed_days: 1,
            overall_index: 1, overall_total: 3, started_at: "2026-06-29T10:00:00Z" },
        ],
        is_running: true,
      },
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sync-progress-banner")).toBeInTheDocument());
    expect(screen.queryByTestId("cancel-sync-button")).not.toBeInTheDocument();
  });

  it("does not poll /status when is_running=false", async () => {
    let statusCalls = 0;
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.startsWith("/api/sync/historical/status")) {
        statusCalls += 1;
        return new Response(
          JSON.stringify({
            as_of: null,
            etfs: [
              {
                code: "510300.XSHG", name: "沪深300ETF",
                last_synced_date: null, last_synced_at: null,
                is_enabled: true, status: "never", error: null, progress: null,
              },
            ],
            in_progress: null, is_running: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("{}", { status: 404 });
    }) as unknown as typeof fetch;

    await act(async () => {
      renderPage();
    });
    await waitFor(() => expect(statusCalls).toBe(1));
    // Wait a real-time tick; should still be 1
    await new Promise((r) => setTimeout(r, 100));
    expect(statusCalls).toBe(1);
  });
});

describe("DynamicPoolPage — useDynamicPoolWithStatus polling behavior", () => {
  // Count GETs to /api/sync/historical/status.
  function installCountingFetchMock(opts: { statusBody?: unknown } = {}) {
    const statusBody = opts.statusBody ?? defaultStatusBody();
    let statusGetCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.startsWith("/api/configs/pool/dynamic/") && method === "PATCH") {
        return new Response(
          JSON.stringify({
            code: decodeURIComponent(url.split("/").pop()!),
            name: "沪深300ETF",
            is_enabled: true,
            last_synced_at: "2026-01-15T10:00:00Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.startsWith("/api/sync/historical/status")) {
        statusGetCount += 1;
        return new Response(JSON.stringify(statusBody), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("{}", { status: 404 });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    return {
      getCount: () => statusGetCount,
      fetchMock,
    };
  }

  describe("with fake timers", () => {
    beforeEach(() => {
      // Only fake setInterval/clearInterval so that React Query's
      // refetchInterval timer is virtual, but waitFor's setTimeout polling
      // remains on real time and can resolve.
      vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it("does not refetch /api/sync/historical/status after 30s of fake time when idle", async () => {
      const { getCount } = installCountingFetchMock();

      renderPage();

      // Initial mount should trigger exactly one GET.
      await waitFor(() => expect(getCount()).toBe(1));

      // Advance well past any would-be polling interval.
      act(() => {
        vi.advanceTimersByTime(30_000);
      });

      // No additional GETs should have fired (idle == no polling).
      expect(getCount()).toBe(1);
    }, 10_000);
  });

  it("refetches /api/sync/historical/status after useToggleDynamicEntry mutation succeeds", async () => {
    const { getCount } = installCountingFetchMock();

    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(getCount()).toBe(1));

    // Toggle the checkbox — this fires PATCH then invalidates
    // ["dynamic-pool-with-status"], which should trigger another GET.
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    const checkbox = row.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox).toBeTruthy();
    await user.click(checkbox);

    await waitFor(() => expect(getCount()).toBeGreaterThan(1));
  });
});

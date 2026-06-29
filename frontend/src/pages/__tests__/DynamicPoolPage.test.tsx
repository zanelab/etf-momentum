import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

function setupFetchMock(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [key, value] of Object.entries(responses)) {
      if (url.startsWith(key)) {
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
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [], in_progress: null, is_running: false },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/动态池/)).toBeInTheDocument());
  });

  it("renders an empty state when no rows", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [],
      "/api/sync/historical/status": { as_of: null, etfs: [], in_progress: null, is_running: false },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/暂无动态池条目/)).toBeInTheDocument());
  });

  it("renders two sync buttons", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [], in_progress: null, is_running: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeInTheDocument();
  });

  it("second button is disabled when pool is empty", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [],
      "/api/sync/historical/status": { as_of: null, etfs: [], in_progress: null, is_running: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeDisabled();
    });
    expect(screen.getByRole("button", { name: "同步 ETF" })).not.toBeDisabled();
  });

  it("row click navigates to /dynamic-pool/:code", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [], in_progress: null, is_running: false },
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    fireEvent.click(row);
    expect(mockNavigate).toHaveBeenCalledWith("/dynamic-pool/510300.XSHG");
  });

  it("checkbox click does NOT navigate", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": { as_of: "2026-01-15", etfs: [], in_progress: null, is_running: false },
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
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": {
        as_of: "2026-01-15",
        etfs: [],
        in_progress: [
          {
            code: "510300", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-20", total_days: 3, completed_days: 2,
            overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
          },
        ],
        is_running: true,
      },
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sync-progress-banner")).toBeInTheDocument());
  });

  it("shows row progress bar when in_progress contains the row's code", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": {
        as_of: "2026-01-15",
        etfs: [],
        in_progress: [
          {
            code: "510300.XSHG", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-20", total_days: 3, completed_days: 2,
            overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
          },
        ],
        is_running: true,
      },
    });
    renderPage();
    const row = await waitFor(() => screen.getByTestId("pool-row-510300.XSHG"));
    expect(row.querySelector('[data-testid="row-progress-bar"]')).toBeTruthy();
  });

  it("disables sync buttons when is_running=true", async () => {
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": {
        as_of: "2026-01-15",
        etfs: [],
        in_progress: [
          {
            code: "510300", from_date: "2024-04-19", to_date: "2024-04-21",
            current_date: "2024-04-20", total_days: 3, completed_days: 2,
            overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
          },
        ],
        is_running: true,
      },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "同步 ETF" })).toBeDisabled();
    });
    expect(screen.getByRole("button", { name: "同步 ETF 历史数据" })).toBeDisabled();
  });

  it("opens DateRangePicker when 历史数据 button clicked; confirm triggers mutate with range", async () => {
    const user = userEvent.setup();
    setupFetchMock({
      "/api/configs/pool/dynamic": [
        { code: "510300.XSHG", name: "沪深300ETF", is_enabled: true, last_synced_at: "2026-01-15T10:00:00Z" },
      ],
      "/api/sync/historical/status": {
        as_of: "2026-01-15",
        etfs: [],
        in_progress: null,
        is_running: false,
      },
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
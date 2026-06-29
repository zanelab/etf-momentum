# Implementation Plan: etf-historical-sync

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-ETF historical-data sync with observability — backend refactors `daily_sync` to take a pool union + record per-ETF status, exposes `GET/POST /api/sync/historical/{status,trigger}`, and frontend adds a `/sync` sidebar page showing per-ETF sync dates with a "立即同步" button.

**Architecture:** Two new HTTP endpoints back a new TanStack-Query-backed React page. The `daily_sync` service is generalized from "all fixtures" to "given code list, latest bar per code", preserving the existing JSON summary file format with an added `status` field per row. `lifespan` keeps auto-running on startup; failures are caught and logged. Pool union (static + dynamic, deduplicated) is read at request time.

**Tech Stack:** FastAPI + Pydantic (backend), TanStack Query + React Router v6 (frontend), Vitest + RTL (frontend tests), pytest (backend tests). No new dependencies.

## Global Constraints

- No new dependencies. Reuse existing patterns (e.g., `useMutation` for trigger, same JSON shape as existing fixtures).
- The two endpoints MUST be safe to call repeatedly (idempotent sync writes) and MUST NOT take more than 5s on the mock path.
- Single commit per task. Commit messages follow `<type>(<scope>): <description>`.
- No `@ts-expect-error`; no `pytest.raises` → 5xx-allow hacks.
- The `daily_sync` JSON output format adds `status` and `error` to each row; existing fields stay.
- `lifespan` MUST NOT crash the app if sync raises.
- Frontend `Sidebar` gets the new "数据同步" entry under the existing `TOOL_ENTRIES` group. Top nav is unchanged (still 仪表盘 + 设置 per dashboard-flatten).
- `useSyncStatus` query key: `["sync-historical-status"]`; `useTriggerSync` invalidates that key on success.
- Backend dev runs `uv run pytest -q` from `backend/`; frontend dev runs `npm test` from `frontend/`. Both must pass per task.

---

## Task 1: Backend — Refactor `daily_sync` to take a code list with per-ETF status

**Files:**
- Modify: `backend/app/services/daily_sync.py`
- Modify: `backend/tests/test_daily_sync.py`

**Interfaces:**

- `sync_historical_for_pool(codes: list[str], target_date: date | None = None) -> Path`
  - Iterates over `codes` (in given order), pulls the latest bar for each via the data-source interface
  - Per row written to JSON: `{code, date, close, volume, money, status, error}`
  - `status` is one of `"ok" | "failed" | "missing"`
  - When status != "ok", `close/volume/money/date` are `null` and `error` is the message (string)
  - Continues on per-code failure — one bad code does not abort the rest
  - `target_date` defaults to today's date in the local timezone (or the latest fixture date in the mock path; for now match the old `sync_today` default behavior — latest bar's date)
  - Returns the path of the written summary JSON

- `sync_today(target_date=None) -> Path` — kept as a thin wrapper that calls `sync_historical_for_pool(codes=<all fixture stems>, target_date=target_date)`. Preserves the existing `main.py` lifespan call.

- [x] **Step 1: Write failing tests** — Add to `backend/tests/test_daily_sync.py`:

```python
def test_sync_historical_for_pool_writes_per_etf_status() -> None:
    from app.services.daily_sync import sync_historical_for_pool
    import json

    codes = ["510300.XSHG", "510500.XSHG"]
    out = sync_historical_for_pool(codes=codes, target_date=date(2026, 3, 1))
    payload = json.loads(out.read_text())
    assert payload["n_etfs"] == 2
    assert {r["code"] for r in payload["rows"]} == set(codes)
    for row in payload["rows"]:
        assert "status" in row
        assert row["status"] == "ok"
        assert row["error"] is None
        assert row["date"] is not None


def test_sync_historical_for_pool_records_failed_without_aborting(tmp_path, monkeypatch) -> None:
    """One code's source raises; other code still syncs; failed row has status=failed + error."""
    from app.services import daily_sync

    def fake_read_latest(code: str):
        if code == "510300.XSHG":
            raise RuntimeError("akshare timeout")
        return {"date": pd.Timestamp("2026-03-19"), "close": 3.9, "volume": 1.0, "money": 1.0}

    monkeypatch.setattr(daily_sync, "_read_latest_bar", fake_read_latest)

    out = daily_sync.sync_historical_for_pool(
        codes=["510300.XSHG", "510500.XSHG"], target_date=date(2026, 3, 1)
    )
    rows = {r["code"]: r for r in json.loads(out.read_text())["rows"]}
    assert rows["510300.XSHG"]["status"] == "failed"
    assert "akshare timeout" in rows["510300.XSHG"]["error"]
    assert rows["510500.XSHG"]["status"] == "ok"


def test_sync_historical_for_pool_marks_missing_code() -> None:
    """A code with no fixture CSV gets status=missing, not failed."""
    from app.services.daily_sync import sync_historical_for_pool
    import json

    out = sync_historical_for_pool(
        codes=["510300.XSHG", "999999.XSHG"], target_date=date(2026, 3, 1)
    )
    rows = {r["code"]: r for r in json.loads(out.read_text())["rows"]}
    assert rows["510300.XSHG"]["status"] == "ok"
    assert rows["999999.XSHG"]["status"] == "missing"
    assert rows["999999.XSHG"]["close"] is None
```

- [x] **Step 2: Run tests, see them fail**

```bash
cd backend && uv run pytest tests/test_daily_sync.py -v
```

Expected: 3 new tests fail with `ImportError: cannot import name 'sync_historical_for_pool'` or attribute error on the new `_read_latest_bar`.

- [x] **Step 3: Implement the refactor** — In `backend/app/services/daily_sync.py`, rewrite so the per-ETF pull becomes a single function `_read_latest_bar(code: str) -> dict | None` that returns the bar dict or `None` when missing, raising on real errors. The main loop catches `Exception` per code, writes the row with `status`/`error` accordingly. Final structure:

```python
import json
from datetime import date
from pathlib import Path

import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"
SYNC_DIR = Path(__file__).resolve().parents[2] / "data" / "daily_sync"


def _read_latest_bar(code: str) -> dict | None:
    """Return {date, close, volume, money} for the latest bar of `code`, or None if missing.

    Mock source: read FIXTURES_DIR/{code}.csv. Production source: delegate to the
    configured MarketDataSource (out of scope for this task — the function is the
    injection point for the real implementation).
    """
    csv_path = FIXTURES_DIR / f"{code}.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, parse_dates=["date"])
    if df.empty:
        return None
    last = df.iloc[-1]
    ts = pd.Timestamp(last["date"])
    return {
        "date": ts.strftime("%Y-%m-%d"),
        "close": float(last["close"]),
        "volume": float(last["volume"]),
        "money": float(last["money"]),
    }


def sync_historical_for_pool(codes: list[str], target_date: date | None = None) -> Path:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for code in codes:
        try:
            bar = _read_latest_bar(code)
        except Exception as e:  # noqa: BLE001 — per-code isolation
            rows.append(
                {"code": code, "date": None, "close": None, "volume": None, "money": None,
                 "status": "failed", "error": str(e)}
            )
            continue
        if bar is None:
            rows.append(
                {"code": code, "date": None, "close": None, "volume": None, "money": None,
                 "status": "missing", "error": None}
            )
            continue
        rows.append({"code": code, **bar, "status": "ok", "error": None})

    sync_date = (target_date or date.today()).isoformat()
    payload = {
        "date": sync_date,
        "n_etfs": len(rows),
        "rows": rows,
    }
    out_path = SYNC_DIR / f"{sync_date}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False))
    return out_path


def sync_today(target_date: date | None = None) -> Path:
    """Backwards-compatible wrapper: sync all fixture codes."""
    codes = sorted(p.stem for p in FIXTURES_DIR.glob("*.csv"))
    return sync_historical_for_pool(codes=codes, target_date=target_date)
```

- [x] **Step 4: Run tests, see them pass**

```bash
cd backend && uv run pytest tests/test_daily_sync.py -v
```

Expected: 5 tests pass (the 2 existing + 3 new). All 165 prior backend tests still pass.

- [x] **Step 5: Commit**

```bash
git add backend/app/services/daily_sync.py backend/tests/test_daily_sync.py
git commit -m "feat(sync): refactor daily_sync to accept pool union with per-ETF status"
```

---

## Task 2: Backend — Sync API endpoints + lifespan hardening

**Files:**
- Create: `backend/app/api/sync.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py` (lifespan catches sync exceptions)
- Create: `backend/tests/test_sync_api.py`

**Interfaces:**

- `GET /api/sync/historical/status` → `SyncStatusResponse`
  ```python
  class SyncETFStatus(BaseModel):
      code: str
      name: str | None
      last_synced_date: str | None
      status: Literal["ok", "failed", "missing", "never"]  # "never" = no summary file yet
      error: str | None = None

  class SyncStatusResponse(BaseModel):
      as_of: str | None
      etfs: list[SyncETFStatus]
  ```
  - Reads the latest `backend/data/daily_sync/{date}.json` summary (any date — pick newest by mtime, since the file's `date` field is the sync date, not the file mtime)
  - Joins with `static_pool` + `dynamic_pool` to compute `name`
  - For each pool code, returns its row from the summary; codes not in the summary get `status="never"`

- `POST /api/sync/historical/trigger` → `SyncTriggerResult`
  ```python
  class SyncTriggerResult(SyncStatusResponse):
      synced_count: int
      run_at: datetime
  ```
  - Calls `sync_historical_for_pool(codes=<pool union>)`
  - Pool union helper: `def pool_union() -> list[str]: ...` reads static + dynamic, deduplicates
  - Returns the trigger result after re-reading the summary

- `lifespan` change in `main.py`:
  ```python
  @asynccontextmanager
  async def lifespan(_app: FastAPI):
      try:
          codes = pool_union()
          if codes:
              sync_historical_for_pool(codes=codes)
      except Exception:
          log.exception("startup historical sync failed; continuing")
      yield
  ```

- [x] **Step 1: Write failing tests** — Create `backend/tests/test_sync_api.py`:

```python
def test_status_endpoint_returns_pool_union(client, monkeypatch) -> None:
    """GET /api/sync/historical/status returns one row per pool code, with name resolved."""
    # Set up: static_pool has 510300, dynamic_pool has 510500
    # Seed: backend/data/daily_sync/2026-03-01.json with both rows status=ok
    # Call: GET /api/sync/historical/status
    # Assert: response.etfs length == 2; rows have code, name, last_synced_date="2026-03-01", status="ok"


def test_status_endpoint_marks_codes_not_in_summary_as_never(client) -> None:
    """If summary file is missing or doesn't list a code, that code gets status=never."""


def test_trigger_endpoint_runs_sync_and_returns_synced_count(client, monkeypatch) -> None:
    """POST /api/sync/historical/trigger calls sync_historical_for_pool and returns synced_count."""
    # Mock sync_historical_for_pool to a fake that writes a known summary
    # Call: POST /api/sync/historical/trigger
    # Assert: response.synced_count == N; response.run_at is set; response.etfs is non-empty


def test_trigger_endpoint_returns_5xx_on_sync_failure(client, monkeypatch) -> None:
    """If the sync function raises, the endpoint returns 500."""
```

The exact fixture setup will mirror `test_dynamic_pool_api.py`'s seeding pattern (use the `client` and `monkeypatch` fixtures; seed static/dynamic pool rows directly via SQLAlchemy session).

- [x] **Step 2: Run tests, see them fail**

```bash
cd backend && uv run pytest tests/test_sync_api.py -v
```

Expected: all 4 fail (file does not exist / routes do not exist).

- [x] **Step 3: Implement endpoints + lifespan hardening**

Create `backend/app/api/sync.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
import json

from app.schemas import SyncETFStatus, SyncStatusResponse, SyncTriggerResult
from app.services.daily_sync import SYNC_DIR, sync_historical_for_pool
from app.models.static_pool import StaticPoolEntry  # if exists
from app.models.dynamic_pool import DynamicPoolEntry

router = APIRouter()


def _pool_union_codes() -> list[str]:
    """Deduplicated union of static_pool and dynamic_pool codes."""
    from app.db import SessionLocal
    codes: set[str] = set()
    with SessionLocal() as s:
        for row in s.query(StaticPoolEntry.code).all():
            codes.add(row[0])
        for row in s.query(DynamicPoolEntry.code).all():
            codes.add(row[0])
    return sorted(codes)


def _name_lookup() -> dict[str, str]:
    from app.db import SessionLocal
    names: dict[str, str] = {}
    with SessionLocal() as s:
        for code, name in s.query(StaticPoolEntry.code, StaticPoolEntry.display_name).all():
            if name:
                names[code] = name
        for code, name in s.query(DynamicPoolEntry.code, DynamicPoolEntry.name).all():
            if name and code not in names:
                names[code] = name
    return names


def _latest_summary() -> tuple[str | None, dict[str, dict]]:
    """Return (as_of, code -> row). Newest by filename; if no file, return (None, {})."""
    if not SYNC_DIR.exists():
        return None, {}
    files = sorted(SYNC_DIR.glob("*.json"), reverse=True)
    if not files:
        return None, {}
    payload = json.loads(files[0].read_text())
    as_of = payload.get("date")
    by_code = {r["code"]: r for r in payload.get("rows", [])}
    return as_of, by_code


@router.get("/sync/historical/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs: list[SyncETFStatus] = []
    for code in _pool_union_codes():
        row = by_code.get(code)
        if row is None:
            etfs.append(SyncETFStatus(code=code, name=names.get(code), last_synced_date=None,
                                       status="never", error=None))
        else:
            etfs.append(SyncETFStatus(
                code=code,
                name=names.get(code),
                last_synced_date=row.get("date"),
                status=row.get("status", "ok"),
                error=row.get("error"),
            ))
    return SyncStatusResponse(as_of=as_of, etfs=etfs)


@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync() -> SyncTriggerResult:
    codes = _pool_union_codes()
    if not codes:
        raise HTTPException(status_code=400, detail="pool is empty; nothing to sync")
    run_at = datetime.now(timezone.utc)
    try:
        sync_historical_for_pool(codes=codes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"sync failed: {e}")
    as_of, by_code = _latest_summary()
    etfs = [
        SyncETFStatus(
            code=code,
            name=_name_lookup().get(code),
            last_synced_date=(by_code.get(code) or {}).get("date"),
            status=(by_code.get(code) or {}).get("status", "missing"),
            error=(by_code.get(code) or {}).get("error"),
        )
        for code in codes
    ]
    synced_count = sum(1 for e in etfs if e.status == "ok")
    return SyncTriggerResult(as_of=as_of, etfs=etfs, synced_count=synced_count, run_at=run_at)
```

Add to `backend/app/schemas.py`:

```python
class SyncETFStatus(BaseModel):
    code: str
    name: str | None
    last_synced_date: str | None
    status: Literal["ok", "failed", "missing", "never"]
    error: str | None = None

class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]

class SyncTriggerResult(SyncStatusResponse):
    synced_count: int
    run_at: datetime
```

Modify `backend/app/main.py`:
- Replace the existing `sync_today()` call in `lifespan` with the try/except + `pool_union` version shown above
- Register the new router: `app.include_router(sync_router, prefix="/api")`

- [x] **Step 4: Run tests, see them pass**

```bash
cd backend && uv run pytest tests/test_sync_api.py tests/test_daily_sync.py -v
```

Expected: all 4 new tests pass; the 3 refactored daily_sync tests still pass; total backend tests = 165 + 4 = 169 (or thereabouts).

- [x] **Step 5: Commit**

```bash
git add backend/app/api/sync.py backend/app/schemas.py backend/app/main.py backend/tests/test_sync_api.py
git commit -m "feat(api): expose /api/sync/historical/{status,trigger} + harden lifespan"
```

---

## Task 3: Frontend — Hooks + types

**Files:**
- Modify: `frontend/src/api/hooks.ts`
- Modify: `frontend/src/api/types.ts` (if separate file — check; otherwise inline in hooks.ts)

**Interfaces:**

```typescript
export type SyncETFStatus = {
  code: string;
  name: string | null;
  last_synced_date: string | null;
  status: "ok" | "failed" | "missing" | "never";
  error: string | null;
};

export type SyncStatusResponse = {
  as_of: string | null;
  etfs: SyncETFStatus[];
};

export type SyncTriggerResult = SyncStatusResponse & {
  synced_count: number;
  run_at: string;
};

export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync-historical-status"],
    queryFn: () => api<SyncStatusResponse>("/api/sync/historical/status"),
    refetchInterval: 10_000,  // slightly slower than the 5s pool pages
  });
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<SyncTriggerResult>("/api/sync/historical/trigger", { method: "POST" }),
    onSuccess: (data) => {
      // Cache the fresh result so the table updates without an extra round-trip
      qc.setQueryData(["sync-historical-status"], data);
      qc.invalidateQueries({ queryKey: ["sync-historical-status"] });
    },
  });
}
```

- [x] **Step 1: Verify tsc still passes after type additions**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. (No new tests for hooks — they are covered by the SyncStatus page tests in Task 4.)

- [x] **Step 2: Implement**

Add the three types and two hooks to `frontend/src/api/hooks.ts` in a new section between `useSignalsToday` and the Backtest section. Match the existing style (5_000 underscore numeric separators, blank lines between sections, etc.).

- [x] **Step 3: Run tsc + lint**

```bash
cd frontend && npx tsc --noEmit
```

Expected: clean.

- [x] **Step 4: Commit**

```bash
git add frontend/src/api/hooks.ts
git commit -m "feat(api): add useSyncStatus + useTriggerSync hooks"
```

---

## Task 4: Frontend — SyncStatus page + sidebar + route

**Files:**
- Create: `frontend/src/pages/SyncStatus.tsx`
- Modify: `frontend/src/components/Sidebar.tsx` (add 数据同步 entry to TOOL_ENTRIES)
- Modify: `frontend/src/App.tsx` (register `/sync` route)

**Interface of `SyncStatus.tsx`:**

```tsx
import { useSyncStatus, useTriggerSync } from "@/api/hooks";

export function SyncStatus() {
  const { data, isLoading, isError } = useSyncStatus();
  const trigger = useTriggerSync();

  const etfs = data?.etfs ?? [];
  const isEmpty = !isLoading && etfs.length === 0;

  return (
    <section className="space-y-4 p-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">数据同步</h1>
          <p className="text-sm text-muted-foreground">
            上次同步：{data?.as_of ?? "—"}
          </p>
        </div>
        <button
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending || etfs.length === 0}
          className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {trigger.isPending ? "同步中…" : "立即同步"}
        </button>
      </header>

      {isLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
      {isError && <p className="text-sm text-red-600">同步状态暂不可用</p>}
      {isEmpty && <p className="text-sm text-muted-foreground">暂无 ETF</p>}

      {etfs.length > 0 && (
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50 text-left">
            <tr>
              <th className="px-2 py-1">代码</th>
              <th className="px-2 py-1">名称</th>
              <th className="px-2 py-1">同步日期</th>
              <th className="px-2 py-1">状态</th>
            </tr>
          </thead>
          <tbody>
            {etfs.map((e) => (
              <tr key={e.code} className="border-b">
                <td className="px-2 py-1 font-mono">{e.code}</td>
                <td className="px-2 py-1">{e.name ?? "—"}</td>
                <td className="px-2 py-1">{e.last_synced_date ?? "—"}</td>
                <td className="px-2 py-1">
                  {e.status === "ok" && <span className="text-green-600">✓ 已同步</span>}
                  {e.status === "failed" && <span className="text-red-600">⚠ 失败</span>}
                  {e.status === "missing" && <span className="text-muted-foreground">— 缺失</span>}
                  {e.status === "never" && <span className="text-muted-foreground">— 未同步</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
```

- [x] **Step 1: Write failing tests** — Create `frontend/src/pages/__tests__/SyncStatus.test.tsx`:

```tsx
// Test 1: Renders table with one row per ETF (mock with 2 ETFs, both ok)
test("renders sync status table with one row per ETF", async () => {
  fetchMock.mockResponseOnce("/api/sync/historical/status",
    JSON.stringify({ as_of: "2026-03-19", etfs: [
      { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-19", status: "ok", error: null },
      { code: "510500.XSHG", name: "中证500ETF", last_synced_date: "2026-03-19", status: "ok", error: null },
    ] }));
  render(<MemoryRouter><SyncStatus /></MemoryRouter>);
  expect(await screen.findByText("510300.XSHG")).toBeInTheDocument();
  expect(screen.getByText("510500.XSHG")).toBeInTheDocument();
  expect(screen.getByText("✓ 已同步")).toBeInTheDocument();
});

// Test 2: Empty state when etfs is empty
test("shows 暂无 ETF when pool is empty", async () => {
  fetchMock.mockResponseOnce(JSON.stringify({ as_of: null, etfs: [] }));
  render(<MemoryRouter><SyncStatus /></MemoryRouter>);
  expect(await screen.findByText("暂无 ETF")).toBeInTheDocument();
});

// Test 3: Click 立即同步 triggers POST and refetches
test("clicking 立即同步 calls POST and updates the table", async () => {
  fetchMock.mockResponseOnce("/api/sync/historical/status",
    JSON.stringify({ as_of: "2026-03-19", etfs: [
      { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-19", status: "ok", error: null },
    ] }));
  // second fetch: status (after trigger refetches)
  fetchMock.mockResponseOnce("/api/sync/historical/status",
    JSON.stringify({ as_of: "2026-03-20", etfs: [
      { code: "510300.XSHG", name: "沪深300ETF", last_synced_date: "2026-03-20", status: "ok", error: null },
    ] }));
  // POST trigger response
  fetchMock.mockResponseOnce("/api/sync/historical/trigger",
    JSON.stringify({ as_of: "2026-03-20", etfs: [...], synced_count: 1, run_at: "2026-03-20T..." }));
  render(<MemoryRouter><SyncStatus /></MemoryRouter>);
  await screen.findByText("510300.XSHG");
  fireEvent.click(screen.getByRole("button", { name: /立即同步/ }));
  expect(await screen.findByText("2026-03-20")).toBeInTheDocument();
});
```

- [x] **Step 2: Run tests, see them fail**

```bash
cd frontend && npm test -- SyncStatus
```

Expected: 3 tests fail (file does not exist).

- [x] **Step 3: Implement the page + register the route + add the sidebar entry**

In `frontend/src/components/Sidebar.tsx`, change:

```ts
const TOOL_ENTRIES = [
  { to: "/backtest", label: "回测" },
  { to: "/history", label: "历史数据" },
  { to: "/datasource", label: "数据源" },
] as const;
```

to:

```ts
const TOOL_ENTRIES = [
  { to: "/backtest", label: "回测" },
  { to: "/history", label: "历史数据" },
  { to: "/sync", label: "数据同步" },
  { to: "/datasource", label: "数据源" },
] as const;
```

In `frontend/src/App.tsx`, add (matching the existing import + route style):

```tsx
import { SyncStatus } from "@/pages/SyncStatus";
// ...
<Route path="/sync" element={<SyncStatus />} />
```

In `frontend/src/pages/SyncStatus.tsx`, paste the component shown in the Interfaces block.

- [x] **Step 4: Run tests, see them pass**

```bash
cd frontend && npm test -- SyncStatus
```

Expected: 3/3 pass.

- [x] **Step 5: Run full frontend suite to confirm no regressions**

```bash
cd frontend && npm test
```

Expected: 30/30 existing + 3 new = 33/33 pass.

- [x] **Step 6: Commit**

```bash
git add frontend/src/pages/SyncStatus.tsx frontend/src/pages/__tests__/SyncStatus.test.tsx \
        frontend/src/components/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat(sync): add /sync page with per-ETF sync status + manual trigger"
```

---

## Task 5: Docs sync

**Files:**
- Modify: `spec/requirements.md` (add new section documenting the etf-historical-sync feature)
- Modify: `spec/devlog.md` (add new entry)

**Content for `spec/requirements.md`** (add after the M11.1 `dashboard-flatten` section):

```markdown
## ETF 历史数据同步可观测（etf-historical-sync 2026-06-29）

- **目标**：解决"某只 ETF 是不是真的同步上了最新一天的数据？"的可观测性盲区
- **数据范围**：`static_pool ∪ dynamic_pool`（去重）；每只 ETF 仅同步最新一根 bar（mock 走 fixtures；akshare 走真实源；接口已抽象为 `_read_latest_bar(code)`，生产实现待后续替换）
- **同步触发**：
  - 启动期（FastAPI `lifespan`）：失败容错，记录日志，**不**阻塞应用
  - 手动：`POST /api/sync/historical/trigger`
- **同步状态**：`ok` / `failed`（含 `error`）/ `missing`（数据源无该 ETF）；失败隔离——单只失败不阻塞其他
- **API**：
  - `GET /api/sync/historical/status` → `{as_of, etfs: [{code, name, last_synced_date, status, error?}]}`；池子未同步过的 ETF 标记 `status: "never"`
  - `POST /api/sync/historical/trigger` → 同 schema + `synced_count` + `run_at`
- **前端**：侧边栏"数据同步"入口 → `/sync`；表格 4 列（代码 | 名称 | 同步日期 | 状态）；状态徽章 `✓ 已同步` / `⚠ 失败` / `— 缺失` / `— 未同步`；立即同步按钮（loading 期间禁用）；空池子显示 `暂无 ETF`
- **持久化**：摘要 JSON 写入 `backend/data/daily_sync/{YYYY-MM-DD}.json`（与原 mock 路径一致，row 扩展 `status` / `error` 字段）
- **测试覆盖**：后端 pytest 169 用例（含本变更新增 4 个：sync_for_pool 3 个 + sync_api 4 个，去重后净增 4 个）；前端 vitest 33 用例（含本变更新增 3 个）
```

**Content for `spec/devlog.md`** (append at the bottom, following the M11.1 entry format):

```markdown
## etf-historical-sync 变更归档

- 日期：2026-06-29（4 个 commit — 1 backend refactor + 1 backend api + 1 frontend hooks + 1 frontend page + 1 docs sync）
- 分支：`feature/etf-historical-sync`（基于 dashboard-flatten HEAD `d21e79d` fast-forward 后的 main）
- 流程归属：openspec（`openspec/changes/etf-historical-sync/{proposal.md, spec.md, plan.md}`）
- 范围：可观测性扩展——为 `static_pool ∪ dynamic_pool` 中每只 ETF 同步最新一根 bar 并暴露状态 API；新增 `/sync` 侧边栏页面
- 关键产物（无 frontend 路由变更 / 无 nav 顶导变更）：
  - **后端服务**：`sync_historical_for_pool(codes)` 替代原 `sync_today()`；后者保留为薄包装；每行新增 `status` / `error` 字段
  - **后端 API**：`GET/POST /api/sync/historical/{status,trigger}`（`backend/app/api/sync.py`）；`lifespan` 启动同步容错化
  - **前端 hooks**：`useSyncStatus()` / `useTriggerSync()`（`@/api/hooks.ts`）
  - **前端页面**：`/sync` 表格 4 列 + 立即同步按钮 + 空池子占位；`Sidebar` 的 `TOOL_ENTRIES` 增补"数据同步"项
- CI 验证：
  - 前端：`npm test` 33 passed（30 既有 + 3 新增）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest -q` 169 passed（165 既有 + 4 新增）/ `uv run ruff check` 通过
- 已知限制（继承 M11.1）：mock 路径仅同步 fixtures；akshare 真实数据源在 `_read_latest_bar` 抽象处替换时需要新增 akshare 调用 + 重试
- 新增/已知 minor（留待后续 M12.x）：
  - `Sidebar` 顺序：原"数据源"在前、新"数据同步"在前（按提交顺序追加），可读性可优化
  - `useSyncStatus` refetchInterval=10s；同步刚完成后未立即刷新到 UI（mutation onSuccess 已 invalidate，可考虑更短 polling）
  - `_read_latest_bar` 接口预留 akshare 注入点；当前实现仅 fixtures
- 下一步：merge 阶段合入 main
```

- [x] **Step 1: Update `spec/requirements.md`** — Append the new section after the `dashboard-flatten` M11.1 section.

- [x] **Step 2: Update `spec/devlog.md`** — Append the new entry at the bottom of the file.

- [x] **Step 3: Commit**

```bash
git add spec/requirements.md spec/devlog.md
git commit -m "chore(etf-historical-sync): sync project-level spec"
```

---

## Final verification (controller's responsibility, not a task)

```bash
cd frontend && npm test && npm run lint && npm run build
cd ../backend && uv run pytest -q && uv run ruff check
```

Manual smoke: visit `/sync`, see the table; click "立即同步" and watch the table update.

Merge step: `git checkout main && git merge --ff-only feature/etf-historical-sync && git branch -d feature/etf-historical-sync`.

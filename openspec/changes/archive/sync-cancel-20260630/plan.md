# Implementation Plan: sync-cancel

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在同步运行中可以取消；后端用 FastAPI BackgroundTasks 异步执行；前端新增「取消」按钮 + cancel 后 banner 变红展示部分进度。

**Architecture:**
- 后端：`SyncProgressTracker` 加 cancel flag；`sync_historical_for_pool` 在每 (code, date) 步后检查 flag 并 break；`trigger_sync` 改用 `BackgroundTasks`；新增 `POST /cancel` 端点
- 前端：新增 `useCancelSync` mutation；`SyncProgressBanner` 接 `isCancelled` prop 渲染红色样式；`DynamicPoolPage` 在 banner 内或 header 加「取消」按钮

**Tech Stack:** FastAPI + Pydantic + BackgroundTasks (backend) + React + TanStack Query + TypeScript (frontend).

## Global Constraints

- 单 commit per task
- 所有既有 191 后端 + 58 前端 测试继续通过（**不修改既有断言**）
- 新增 ≤ 8 后端 + ≤ 4 前端 测试，TDD
- 不引入新依赖
- tsc --noEmit / npm run build / uv run ruff check 干净
- `SyncStatusResponse` / `SyncTriggerResult` 新字段 Optional，向后兼容
- `is_cancelled` schema 字段仅在 cancel 后短暂为 true（status poll 时已清）；前端用它决定 banner 颜色
- trigger 改为 BackgroundTasks 后，trigger 响应不再包含 synced_count / etfs（虽然 schema 仍允许，但实际值是初始 0 / 空）

---

## Task 1: 后端 — `SyncProgressTracker` cancel flag + 单元测试

**Files:**
- Modify: `backend/app/services/sync_progress.py`
- Modify: `backend/tests/services/test_sync_progress_tracker.py`（既有 5 个 + 新增 4 个 cancel 用例）

**Interfaces:**

```python
class SyncProgressTracker:
    def __init__(self) -> None:
        self._by_code: dict[str, ProgressInfo] = {}
        self._cancel_requested: bool = False

    def set(self, code: str, info: ProgressInfo) -> None: ...
    def get_all(self) -> list[ProgressInfo]: ...
    def clear(self) -> None:
        self._by_code.clear()
        self._cancel_requested = False  # also reset cancel on clear

    def is_active(self) -> bool: ...

    # 新增
    def cancel(self) -> None:
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def reset_cancel(self) -> None:
        self._cancel_requested = False
```

- [x] **Step 1: 写新测试（RED）**

在 `backend/tests/services/test_sync_progress_tracker.py` 末尾新增：

```python
def test_tracker_cancel_starts_false():
    t = SyncProgressTracker()
    assert t.is_cancel_requested() is False

def test_tracker_cancel_sets_flag():
    t = SyncProgressTracker()
    t.cancel()
    assert t.is_cancel_requested() is True

def test_tracker_reset_cancel_clears_flag():
    t = SyncProgressTracker()
    t.cancel()
    t.reset_cancel()
    assert t.is_cancel_requested() is False

def test_tracker_clear_also_resets_cancel():
    """clear() 是 sync 完成时的清理点，应同时清除 cancel flag。"""
    t = SyncProgressTracker()
    info = ProgressInfo(code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
                        current_date=date(2024,1,1), total_days=31, completed_days=1,
                        overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc))
    t.set("510300", info)
    t.cancel()
    t.clear()
    assert t.is_cancel_requested() is False
    assert t.is_active() is False
```

- [x] **Step 2: 跑新测试验证 RED**

```bash
cd backend && uv run pytest tests/services/test_sync_progress_tracker.py -v
```

Expected: 4 个新测试全 FAIL（方法不存在）

- [x] **Step 3: 实现 cancel flag（GREEN）**

修改 `backend/app/services/sync_progress.py`：

```python
class SyncProgressTracker:
    def __init__(self) -> None:
        self._by_code: dict[str, ProgressInfo] = {}
        self._cancel_requested: bool = False

    def set(self, code: str, info: ProgressInfo) -> None:
        self._by_code[code] = info

    def get_all(self) -> list[ProgressInfo]:
        return list(self._by_code.values())

    def clear(self) -> None:
        self._by_code.clear()
        self._cancel_requested = False

    def is_active(self) -> bool:
        return bool(self._by_code)

    def cancel(self) -> None:
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def reset_cancel(self) -> None:
        self._cancel_requested = False
```

- [x] **Step 4: 跑新测试验证 GREEN**

```bash
uv run pytest tests/services/test_sync_progress_tracker.py -v
```

Expected: 9/9 passed (5 既有 + 4 新增)

- [x] **Step 5: 跑后端全量确认无回归**

```bash
uv run pytest -q && uv run ruff check
```

Expected: 191 passed / ruff clean

- [x] **Step 6: 提交**

```bash
git add backend/app/services/sync_progress.py backend/tests/services/test_sync_progress_tracker.py
git commit -m "feat(sync-cancel): add cancel flag to SyncProgressTracker"
```

---

## Task 2: 后端 — `sync_historical_for_pool` 支持 cancel + 测试

**Files:**
- Modify: `backend/app/services/daily_sync.py`（在每 (code, date) 步后检查 `tracker.is_cancel_requested()`；cancel 时 break 双层循环；不调用 `tracker.clear()` 让前端通过 status 看到最后一次状态；reset cancel flag 在 sync 开始时）
- Modify: `backend/tests/test_daily_sync.py`（新增 2 个测试：cancel 中断；cancel 后不 clear tracker）

**Interfaces:**

```python
# sync_historical_for_pool 关键改动
def sync_historical_for_pool(codes, from_date, to_date) -> Path:
    # ... 既有 setup ...
    tracker.reset_cancel()  # 防御：sync 开始时清 cancel flag（防止上次残留）

    for code in codes:
        for offset in range(total_days):
            # ... 既有 bar read + status 写入 rows ...

            overall_index += 1
            tracker.set(code, ProgressInfo(...))

            # 新增：每步后检查 cancel
            if tracker.is_cancel_requested():
                # 中断：rows 保留已完成的；summary 仍写
                break  # break inner
        else:
            continue  # inner 没 break
        break  # outer break if inner broke

    # 既有 summary 写入（cancel 也写）
    ...
    return out_path
```

注意：
- 不要在 cancel break 后调 `tracker.clear()`（让前端 status poll 看到「最后一次状态」，banner 渲染取消样式）
- cancel 后下一次 `trigger_sync` 会先 `tracker.reset_cancel()` 清掉旧 flag
- summary JSON 仍写，包含部分 rows

- [x] **Step 1: 写新测试（RED）**

在 `backend/tests/test_daily_sync.py` 末尾新增：

```python
def test_sync_historical_for_pool_respects_cancel(tmp_path, monkeypatch):
    """When cancel is requested mid-loop, sync stops and writes partial summary."""
    from app.services import daily_sync
    from app.services.sync_progress import ProgressInfo, tracker
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    tracker.clear()

    # 模拟 cancel 在第 4 步后触发
    original_set = tracker.set
    call_count = {"n": 0}
    def fake_set(code, info):
        call_count["n"] += 1
        if call_count["n"] == 4:
            tracker.cancel()
        original_set(code, info)
    monkeypatch.setattr(tracker, "set", fake_set)

    codes = ["159915.XSHE", "510300.XSHG"]
    out = sync_historical_for_pool(
        codes=codes, from_date=date(2024, 4, 19), to_date=date(2024, 4, 21),
    )

    # summary 写入了
    assert out.exists()
    payload = json.loads(out.read_text())
    # 部分 rows（4 个完成）
    assert len(payload["rows"]) == 4
    # tracker 未清（让前端看到 cancel 状态）
    assert tracker.is_active() is True
    assert tracker.is_cancel_requested() is True
    tracker.clear()


def test_sync_historical_for_pool_resets_cancel_at_start(tmp_path, monkeypatch):
    """If cancel flag was set from a previous run, sync resets it at start."""
    from app.services import daily_sync
    from app.services.sync_progress import tracker
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    tracker.clear()
    tracker.cancel()  # simulate stale flag
    assert tracker.is_cancel_requested() is True

    # Run a 1-code 1-day sync
    sync_historical_for_pool(
        codes=["159915.XSHE"], from_date=date(2024, 4, 19), to_date=date(2024, 4, 19),
    )
    # After completion, cancel flag should be reset (by clear() called in api layer or by reset_cancel at start)
    # Here we only test the reset_cancel call, not the clear
    assert tracker.is_cancel_requested() is False
    tracker.clear()
```

- [x] **Step 2: 跑新测试验证 RED**

```bash
uv run pytest tests/test_daily_sync.py -v
```

Expected: 2 个新测试 FAIL（cancel check 不存在）

- [ ] **Step 3: 实现 cancel 检查**

修改 `sync_historical_for_pool`：

```python
def sync_historical_for_pool(codes, from_date, to_date) -> Path:
    from app.services.sync_progress import ProgressInfo, tracker

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    tracker.reset_cancel()  # 新增：sync 开始时清 stale cancel flag

    total_days = (to_date - from_date).days + 1
    overall_total = total_days * len(codes)
    overall_index = 0
    started_at = datetime.now(timezone.utc)
    rows: list[dict] = []

    for code in codes:
        for offset in range(total_days):
            current_date = from_date + timedelta(days=offset)
            try:
                bar = _read_bar_for_date(code, current_date)
            except Exception as e:
                rows.append({
                    "code": code, "date": current_date.isoformat(),
                    "close": None, "volume": None, "money": None,
                    "status": "failed", "error": str(e),
                })
            else:
                if bar is None:
                    rows.append({
                        "code": code, "date": current_date.isoformat(),
                        "close": None, "volume": None, "money": None,
                        "status": "missing", "error": None,
                    })
                else:
                    rows.append({
                        "code": code, "date": bar["date"],
                        "close": bar["close"], "volume": bar["volume"], "money": bar["money"],
                        "status": "ok", "error": None,
                    })

            overall_index += 1
            tracker.set(code, ProgressInfo(
                code=code,
                from_date=from_date, to_date=to_date,
                current_date=current_date,
                total_days=total_days, completed_days=offset + 1,
                overall_index=overall_index, overall_total=overall_total,
                started_at=started_at,
            ))

            # 新增：每步后检查 cancel
            if tracker.is_cancel_requested():
                break  # break inner
        else:
            continue  # inner completed normally
        break  # outer break if inner was cancelled

    # summary 写入（cancel 也写）
    payload = {
        "date": to_date.isoformat(),
        "n_etfs": len(codes),
        "rows": rows,
    }
    out_path = SYNC_DIR / f"{to_date.isoformat()}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False))
    return out_path
```

- [ ] **Step 4: 跑新测试验证 GREEN**

```bash
uv run pytest tests/test_daily_sync.py -v
```

Expected: 既有 + 新增 2 个 = 全通过

- [ ] **Step 5: 跑后端全量**

```bash
uv run pytest -q && uv run ruff check
```

Expected: 193 passed (191 + 2) / ruff clean

- [x] **Step 6: 提交**

```bash
git add backend/app/services/daily_sync.py backend/tests/test_daily_sync.py
git commit -m "feat(sync-cancel): sync_historical_for_pool respects cancel flag"
```

---

## Task 3: 后端 — `trigger_sync` 改用 BackgroundTasks + `/cancel` 端点 + 测试

**Files:**
- Modify: `backend/app/api/sync.py`：
  - `trigger_sync` 用 `BackgroundTasks`（从 `fastapi` import）
  - 新增 `POST /sync/historical/cancel` 端点
  - `SyncStatusResponse` 加 `is_cancelled: bool = False` 字段
- Modify: `backend/app/schemas.py`：`SyncStatusResponse` 加 `is_cancelled: bool = False`
- Create: `backend/tests/api/test_sync_cancel.py`（新文件，3-4 个测试）

**Interfaces:**

```python
# schemas.py
class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]
    in_progress: list[ProgressInfo] | None = None
    is_running: bool = False
    is_cancelled: bool = False  # 新增，Optional 向后兼容


# api/sync.py
from fastapi import BackgroundTasks

@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(
    background: BackgroundTasks,
    from_date: date_type = Query(...),
    to_date: date_type = Query(...),
) -> SyncTriggerResult:
    """验证 + 启动后台 sync + 立即返回（不阻塞）"""
    if from_date > to_date:
        raise HTTPException(400, "from_date must be ≤ to_date")
    if from_date > date_type.today():
        raise HTTPException(400, "from_date cannot be in the future")
    if (to_date - from_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(400, f"date range too large (max {MAX_RANGE_DAYS} days)")
    if tracker.is_active():
        raise HTTPException(400, "sync already running")

    codes = _pool_union_codes()
    if not codes:
        raise HTTPException(400, "pool is empty; nothing to sync")

    # 后台执行；trigger 立即返回
    background.add_task(sync_historical_for_pool, codes=codes, from_date=from_date, to_date=to_date)

    return SyncTriggerResult(
        as_of=None,
        etfs=[],
        in_progress=[],
        is_running=True,
        synced_count=0,
        run_at=datetime.now(timezone.utc),
        from_date=from_date,
        to_date=to_date,
    )


@router.post("/sync/historical/cancel", response_model=CancelResult)
def cancel_sync() -> CancelResult:
    """请求取消正在运行的 sync。返回 400 如果没有 sync 在跑。"""
    if not tracker.is_active():
        raise HTTPException(400, "no sync running")
    tracker.cancel()
    return CancelResult(cancelled=True)
```

新 schema：
```python
class CancelResult(BaseModel):
    cancelled: bool
```

- [x] **Step 1: 写新测试（RED）**

创建 `backend/tests/api/test_sync_cancel.py`：

```python
"""Tests for the cancel sync endpoint + trigger async behavior."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.sync_progress import tracker, ProgressInfo
from datetime import date, datetime, timezone


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_tracker():
    tracker.clear()
    yield
    tracker.clear()


def test_cancel_returns_400_when_no_sync_running(client):
    r = client.post("/api/sync/historical/cancel")
    assert r.status_code == 400
    assert "no sync running" in r.json()["detail"]


def test_cancel_returns_200_and_sets_flag(client):
    # Pre-populate tracker to simulate running sync
    tracker.set("510300", ProgressInfo(
        code="510300", from_date=date(2024,4,19), to_date=date(2024,4,21),
        current_date=date(2024,4,20), total_days=3, completed_days=2,
        overall_index=2, overall_total=3,
        started_at=datetime.now(timezone.utc),
    ))
    r = client.post("/api/sync/historical/cancel")
    assert r.status_code == 200
    assert r.json() == {"cancelled": True}
    assert tracker.is_cancel_requested() is True


def test_trigger_returns_immediately_with_is_running_true(client):
    """trigger 不应阻塞：返回 is_running=true 但 in_progress=[]."""
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-04-19", "to_date": "2024-04-21"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is True
    assert body["in_progress"] == []
    assert body["synced_count"] == 0


def test_status_returns_is_cancelled_after_cancel(client):
    """Cancel 后 status 反映 is_cancelled=true（直到下次 sync 启动清除）."""
    tracker.set("510300", ProgressInfo(
        code="510300", from_date=date(2024,4,19), to_date=date(2024,4,21),
        current_date=date(2024,4,20), total_days=3, completed_days=2,
        overall_index=2, overall_total=3,
        started_at=datetime.now(timezone.utc),
    ))
    tracker.cancel()
    r = client.get("/api/sync/historical/status")
    assert r.status_code == 200
    body = r.json()
    assert body["is_cancelled"] is True
    assert body["is_running"] is True  # still running until cancel propagates
```

- [x] **Step 2: 跑新测试验证 RED**

```bash
uv run pytest tests/api/test_sync_cancel.py -v
```

Expected: 4 个新测试全 FAIL（cancel 端点不存在 / trigger 阻塞 / is_cancelled 字段不存在）

- [x] **Step 3: 修改 schemas.py**

```python
class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]
    in_progress: list[ProgressInfo] | None = None
    is_running: bool = False
    is_cancelled: bool = False  # 新增


class CancelResult(BaseModel):
    cancelled: bool
```

- [ ] **Step 4: 修改 api/sync.py**

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from app.schemas import SyncETFStatus, SyncStatusResponse, SyncTriggerResult, CancelResult
# ... 既有 imports

# 顶部加新 schema import
class CancelResult(BaseModel):
    cancelled: bool


@router.post("/sync/historical/cancel", response_model=CancelResult)
def cancel_sync() -> CancelResult:
    if not tracker.is_active():
        raise HTTPException(400, "no sync running")
    tracker.cancel()
    return CancelResult(cancelled=True)


@router.get("/sync/historical/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(_pool_union_codes(), names, by_code)
    in_progress = tracker.get_all() if tracker.is_active() else None
    is_cancelled = tracker.is_cancel_requested()
    return SyncStatusResponse(
        as_of=as_of,
        etfs=etfs,
        in_progress=in_progress,
        is_running=tracker.is_active(),
        is_cancelled=is_cancelled,
    )


@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(
    background: BackgroundTasks,
    from_date: date_type = Query(...),
    to_date: date_type = Query(...),
) -> SyncTriggerResult:
    """验证 + 启动后台 sync + 立即返回。"""
    if from_date > to_date:
        raise HTTPException(400, "from_date must be ≤ to_date")
    if from_date > date_type.today():
        raise HTTPException(400, "from_date cannot be in the future")
    if (to_date - from_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(400, f"date range too large (max {MAX_RANGE_DAYS} days)")
    if tracker.is_active():
        raise HTTPException(400, "sync already running")

    codes = _pool_union_codes()
    if not codes:
        raise HTTPException(400, "pool is empty; nothing to sync")

    background.add_task(sync_historical_for_pool, codes=codes, from_date=from_date, to_date=to_date)

    return SyncTriggerResult(
        as_of=None,
        etfs=[],
        in_progress=[],
        is_running=True,
        synced_count=0,
        run_at=datetime.now(timezone.utc),
        from_date=from_date,
        to_date=to_date,
    )
```

- [x] **Step 5: 跑新测试验证 GREEN**

```bash
uv run pytest tests/api/test_sync_cancel.py -v
```

Expected: 4/4 passed

- [x] **Step 6: 跑后端全量**

```bash
uv run pytest -q && uv run ruff check
```

Expected: 197 passed (191 + 2 + 4) / ruff clean

- [x] **Step 7: 提交**

```bash
git add backend/app/schemas.py backend/app/api/sync.py backend/tests/api/test_sync_cancel.py
git commit -m "feat(sync-cancel): trigger uses BackgroundTasks + cancel endpoint"
```

---

## Task 4: 前端 — `useCancelSync` hook + `SyncStatusResponse` 扩展

**Files:**
- Modify: `frontend/src/api/hooks.ts`：
  - `SyncStatusResponse` 加 `is_cancelled: boolean`
  - 新增 `useCancelSync()` mutation
  - `useTriggerSync` onSuccess 移除 `setQueryData`（让 status poll 独占显示）
- Create: `frontend/src/api/__tests__/hooks.cancel.test.tsx`（1 个 mutation 测试）

**Interfaces:**

```ts
// hooks.ts
export type SyncStatusResponse = {
  as_of: string | null;
  etfs: SyncETFStatus[];
  in_progress: ProgressInfo[] | null;
  is_running: boolean;
  is_cancelled: boolean;  // 新增
};

export interface CancelResult {
  cancelled: boolean;
}

export function useCancelSync() {
  const qc = useQueryClient();
  return useMutation<CancelResult, Error, void>({
    mutationFn: () => api<CancelResult>("/api/sync/historical/cancel", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sync-historical-status"] });
    },
  });
}

// useTriggerSync 改动
export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation<SyncTriggerResult, Error, SyncTriggerVariables>({
    mutationFn: ({ from_date, to_date }) =>
      api<SyncTriggerResult>(
        `/api/sync/historical/trigger?from_date=${from_date}&to_date=${to_date}`,
        { method: "POST" },
      ),
    onSuccess: () => {
      // 不再 setQueryData（避免覆盖 status poll 的真实进度）
      qc.invalidateQueries({ queryKey: ["sync-historical-status"] });
    },
  });
}
```

- [x] **Step 1: 写 mutation 测试（RED）**

`frontend/src/api/__tests__/hooks.cancel.test.tsx`：

```tsx
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { describe, expect, it, beforeAll, afterAll, afterEach } from "vitest";
import { useCancelSync } from "../hooks";

const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCancelSync", () => {
  it("POSTs to /api/sync/historical/cancel and returns cancelled=true", async () => {
    let capturedUrl: string | null = null;
    server.use(
      http.post("*/api/sync/historical/cancel", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ cancelled: true });
      })
    );
    const { result } = renderHook(() => useCancelSync(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedUrl).toContain("/api/sync/historical/cancel");
    expect(result.current.data).toEqual({ cancelled: true });
  });
});
```

- [x] **Step 2: 跑测试验证 RED**

```bash
cd frontend && npx vitest run src/api/__tests__/hooks.cancel.test.tsx
```

Expected: 1 个测试 FAIL

- [ ] **Step 3: 修改 hooks.ts**

按上述 interface 实现。`SyncStatusResponse` 加 `is_cancelled`；新增 `useCancelSync`；`useTriggerSync.onSuccess` 移除 `setQueryData`。

- [ ] **Step 4: 跑测试验证 GREEN**

```bash
npx vitest run src/api/__tests__/hooks.cancel.test.tsx
```

Expected: 1/1 passed

- [x] **Step 5: 跑前端全量 + tsc + build**

```bash
npx vitest run && npx tsc --noEmit && npm run build
```

Expected: 既有 58 + 1 新增 = 59/59 passed

- [x] **Step 6: 提交**

```bash
git add frontend/src/api/hooks.ts frontend/src/api/__tests__/hooks.cancel.test.tsx
git commit -m "feat(sync-cancel): add useCancelSync hook + extend SyncStatusResponse"
```

---

## Task 5: 前端 — `SyncProgressBanner` 接 isCancelled + `DynamicPoolPage` 取消按钮

**Files:**
- Modify: `frontend/src/components/SyncProgressBanner.tsx`（接 `isCancelled` prop，true 时渲染红色「已取消」样式）
- Modify: `frontend/src/pages/DynamicPoolPage.tsx`（接 `useCancelSync`；在 banner 内或 header 加「取消」按钮）
- Modify: `frontend/src/components/__tests__/SyncProgressBanner.test.tsx`（新增 1-2 个 isCancelled 测试）
- Modify: `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（新增 1-2 个 cancel 流程测试）

**Interfaces:**

```tsx
// SyncProgressBanner.tsx
export function SyncProgressBanner({
  progress,
  isCancelled = false,
}: {
  progress: ProgressInfo[];
  isCancelled?: boolean;
}) {
  if (progress.length === 0) return null;
  const total = progress[0].overall_total;
  const done = Math.max(...progress.map((p) => p.overall_index));
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  const current = progress.reduce((a, b) => (a.overall_index >= b.overall_index ? a : b));

  const bgColor = isCancelled ? "bg-red-50 border-red-300" : "bg-blue-50";
  const barColor = isCancelled ? "bg-red-500" : "bg-blue-500";
  const headerText = isCancelled ? "已取消" : "同步进行中";

  return (
    <div className={`rounded border p-3 text-sm ${bgColor}`} data-testid="sync-progress-banner">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-medium">{headerText}</span>
        <span className="text-muted-foreground">{done} / {total} ({percent}%)</span>
      </div>
      <div className={`mb-2 h-2 w-full overflow-hidden rounded ${isCancelled ? "bg-red-100" : "bg-blue-100"}`}>
        <div className={`h-full transition-all ${barColor}`} style={{ width: `${percent}%` }} />
      </div>
      <div className="text-xs text-muted-foreground">
        {isCancelled ? "已同步" : "当前"}：<span className="font-mono">{current.code}</span>{" "}
        {current.current_date} / 共 {current.total_days} 天
      </div>
    </div>
  );
}


// DynamicPoolPage.tsx 改动
const cancelSync = useCancelSync();
// ...
const isCancelled = syncStatus.data?.is_cancelled ?? false;
// ...
{inProgress.length > 0 && (
  <SyncProgressBanner progress={inProgress} isCancelled={isCancelled} />
)}
// 取消按钮放在 banner 旁边或内嵌
{inProgress.length > 0 && !isCancelled && (
  <button
    type="button"
    onClick={() => cancelSync.mutate()}
    disabled={cancelSync.isPending}
    className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700 disabled:opacity-50"
    data-testid="cancel-sync-button"
  >
    取消
  </button>
)}
```

- [x] **Step 1: 写 SyncProgressBanner 新测试（RED）**

`frontend/src/components/__tests__/SyncProgressBanner.test.tsx` 新增：

```tsx
it("renders red cancelled style when isCancelled=true", () => {
  const { container } = render(<SyncProgressBanner progress={sampleProgress} isCancelled={true} />);
  expect(container.firstChild).toHaveClass("bg-red-50");
  expect(screen.getByText(/已取消/)).toBeInTheDocument();
});

it("renders blue progress style when isCancelled=false", () => {
  const { container } = render(<SyncProgressBanner progress={sampleProgress} isCancelled={false} />);
  expect(container.firstChild).toHaveClass("bg-blue-50");
  expect(screen.getByText(/同步进行中/)).toBeInTheDocument();
});
```

- [x] **Step 2: 写 DynamicPoolPage 新测试（RED）**

`frontend/src/pages/__tests__/DynamicPoolPage.test.tsx` 新增：

```tsx
it("shows cancel button when in_progress is non-empty and not cancelled", async () => {
  // mock status returns in_progress with 1 entry
  server.use(
    http.get("*/api/sync/historical/status", () => HttpResponse.json({
      as_of: "2024-04-21", etfs: [],
      in_progress: [/* ... */],
      is_running: true, is_cancelled: false,
    }))
  );
  // ... render and assert cancel button exists
});

it("clicking cancel button calls useCancelSync", async () => {
  // mock cancel endpoint + status
  // ... render, click cancel, assert cancel endpoint called
});
```

- [x] **Step 3: 跑新测试验证 RED**

```bash
npx vitest run src/components/__tests__/SyncProgressBanner.test.tsx src/pages/__tests__/DynamicPoolPage.test.tsx
```

Expected: 新增测试 FAIL

- [x] **Step 4: 实现 SyncProgressBanner 修改**

按上述 interface 修改。

- [x] **Step 5: 实现 DynamicPoolPage 修改**

按上述 interface 修改：接 `useCancelSync`；banner 加 `isCancelled`；新增取消按钮（位置在 banner 下方或内嵌）。

- [x] **Step 6: 跑新测试验证 GREEN**

```bash
npx vitest run src/components/__tests__/SyncProgressBanner.test.tsx src/pages/__tests__/DynamicPoolPage.test.tsx
```

Expected: 新增测试通过；既有测试也通过

- [x] **Step 7: 跑前端全量 + tsc + build**

```bash
npx vitest run && npx tsc --noEmit && npm run build
```

Expected: 既有 58 + 1 (Task 4) + 新增 = 60+ passed / tsc / build 全绿

- [x] **Step 8: 提交**

```bash
git add frontend/src/components/SyncProgressBanner.tsx frontend/src/pages/DynamicPoolPage.tsx \
        frontend/src/components/__tests__/SyncProgressBanner.test.tsx \
        frontend/src/pages/__tests__/DynamicPoolPage.test.tsx
git commit -m "feat(sync-cancel): cancel button + banner red cancelled state"
```

---

## Task 6: 全量验证 + 手动 smoke + 收尾

**Files:** 无新文件

- [x] **Step 1: 跑后端全量 + ruff**

```bash
cd backend && uv run pytest -q && uv run ruff check
```

Expected: 197 passed / ruff clean

- [ ] **Step 2: 跑前端全量 + tsc + build**

```bash
cd frontend && npx vitest run && npx tsc --noEmit && npm run build
```

Expected: 既有 + 新增 = 全通过 / tsc / build 全绿

- [x] **Step 3: 手动浏览器 smoke（人工，必做）**

启动 dev server，验证：
1. 点「同步 ETF 历史数据」→ 选范围 → 点「开始同步」→ Modal 立即关闭
2. 顶部 banner 出现，显示进度
3. 取消按钮可见，点击 → 10s 内 status 轮询看到 `is_running=false`
4. banner 变红显示「已取消 — 已同步 X / Y」
5. 立即可重新触发新 sync
6. 同步未运行时 POST /cancel → 400

- [x] **Step 4: 跑 final review（subagent-driven-development）**

- [ ] **Step 5: 修复 review 发现的 Critical / Important 问题（如有）**

- [ ] **Step 6: 准备合并**

```bash
git log --oneline main..HEAD
git status
```

---

## 风险与缓解

- **BackgroundTasks 跨进程重启丢失**（低）：mock 路径无影响；前端 status poll 看到 `is_running=false` 后 UI 复位
- **`useTriggerSync` 移除 setQueryData 导致「空状态」瞬间**（低）：trigger 响应带 `is_running=true, in_progress=[]`；前端 10s 内 status poll 拿到真实进度
- **cancel race：cancel 到达时 sync 恰好完成**（低）：cancel 端检查 `tracker.is_active()`，如果 sync 已完成 tracker 已 clear，会返回 400
- **`_read_bar_for_date` 在 cancel flag 检查前阻塞 I/O**（低）：mock 路径 < 1ms/步；真实 I/O 可能 50-200ms 延迟；本期接受这个粒度

---

**Report 文件**: `/Users/zane/Workspace/etf-momentum/.superpowers/sdd/sc-task-N-report.md`（N = 1..6）
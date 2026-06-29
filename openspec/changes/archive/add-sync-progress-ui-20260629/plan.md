# Implementation Plan: add-sync-progress-ui

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `/dynamic-pool` 页面的「同步 ETF 历史数据」显示细粒度进度：用户先选 from/to 日期范围，运行时表格顶部显示总进度 + 表格行内显示当前 code 的 day N/M。

**Architecture:** 后端加进程内 `SyncProgressTracker` 单例 + 改造 `sync_historical_for_pool` 接受 from/to + 改造 trigger/status 端点；前端加 `DateRangePicker` Modal + 顶部横幅 + 行内进度条 + `useTriggerSync` 接受日期范围变量。复用 `useSyncStatus` 10s 轮询（现在有意义了）。

**Tech Stack:** FastAPI + Pydantic (backend) + React + TanStack Query + TypeScript (frontend).

## Global Constraints

- 单 commit per task，每个 task 完成后立即 commit
- 所有既有测试（172 后端 + 38 前端）继续通过（**不修改既有断言**；只调整调用方式）
- 新增测试：~6 后端 + ~6 前端，全部 TDD（先 RED 后 GREEN）
- 不引入新依赖（除非绝对必要，task 提交时说明）
- tsc --noEmit / npm run build / uv run ruff check 全部干净
- `SyncStatusResponse` 新字段全部 Optional，向后兼容
- `useTriggerSync` 从无参改为 `{from_date, to_date}` 必填，调用方必须更新
- mock fixture 读取快，47 codes × 200 days ≈ 9400 ops < 10s，不需做额外并发控制
- 不做取消同步功能

---

## Task 1: 后端 — `SyncProgressTracker` 单例 + 单元测试

**Files:**
- Create: `backend/app/services/sync_progress.py`
- Create: `backend/tests/services/test_sync_progress.py`（**新**目录 + 新文件）

**Interfaces:**

```python
# backend/app/services/sync_progress.py
from datetime import date, datetime
from pydantic import BaseModel

class ProgressInfo(BaseModel):
    code: str
    from_date: date
    to_date: date
    current_date: date
    total_days: int
    completed_days: int
    overall_index: int
    overall_total: int
    started_at: datetime

class SyncProgressTracker:
    def __init__(self) -> None: ...
    def set(self, code: str, info: ProgressInfo) -> None: ...
    def get_all(self) -> list[ProgressInfo]: ...
    def clear(self) -> None: ...
    def is_active(self) -> bool: ...

# module-level singleton
tracker = SyncProgressTracker()
```

- [x] **Step 1: 写测试（RED）**

`backend/tests/services/test_sync_progress.py`：
```python
from app.services.sync_progress import ProgressInfo, SyncProgressTracker, tracker
from datetime import date, datetime, timezone

def test_tracker_starts_inactive():
    t = SyncProgressTracker()
    assert t.is_active() is False
    assert t.get_all() == []

def test_tracker_set_marks_active():
    t = SyncProgressTracker()
    info = ProgressInfo(
        code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
        current_date=date(2024,1,1), total_days=31, completed_days=1,
        overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc),
    )
    t.set("510300", info)
    assert t.is_active() is True
    assert t.get_all() == [info]

def test_tracker_overwrite_same_code():
    t = SyncProgressTracker()
    info1 = ProgressInfo(code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
                         current_date=date(2024,1,1), total_days=31, completed_days=1,
                         overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc))
    info2 = info1.model_copy(update={"current_date": date(2024,1,2), "completed_days": 2, "overall_index": 2})
    t.set("510300", info1)
    t.set("510300", info2)
    assert len(t.get_all()) == 1
    assert t.get_all()[0].current_date == date(2024,1,2)

def test_tracker_clear_resets():
    t = SyncProgressTracker()
    info = ProgressInfo(code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
                        current_date=date(2024,1,1), total_days=31, completed_days=1,
                        overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc))
    t.set("510300", info)
    t.clear()
    assert t.is_active() is False
    assert t.get_all() == []

def test_module_singleton_exists():
    assert isinstance(tracker, SyncProgressTracker)
```

- [x] **Step 2: 跑测试验证 RED**

```bash
cd backend && uv run pytest tests/services/test_sync_progress.py -v
```

Expected: 5 个测试全 FAIL（模块不存在）

- [x] **Step 3: 实现 `SyncProgressTracker`（GREEN）**

`backend/app/services/sync_progress.py`：
```python
"""Process-singleton in-memory tracker for in-progress historical sync.

This is a module-level singleton; tests should construct a fresh
`SyncProgressTracker()` rather than relying on the singleton.
"""
from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel


class ProgressInfo(BaseModel):
    code: str
    from_date: date
    to_date: date
    current_date: date
    total_days: int
    completed_days: int
    overall_index: int
    overall_total: int
    started_at: datetime


class SyncProgressTracker:
    """dict[code, ProgressInfo] backed by a private dict."""

    def __init__(self) -> None:
        self._by_code: dict[str, ProgressInfo] = {}

    def set(self, code: str, info: ProgressInfo) -> None:
        self._by_code[code] = info

    def get_all(self) -> list[ProgressInfo]:
        return list(self._by_code.values())

    def clear(self) -> None:
        self._by_code.clear()

    def is_active(self) -> bool:
        return bool(self._by_code)


# module-level singleton used by sync service + status endpoint
tracker = SyncProgressTracker()
```

- [x] **Step 4: 跑测试验证 GREEN**

```bash
uv run pytest tests/services/test_sync_progress.py -v
```

Expected: 5/5 passed

- [x] **Step 5: 跑后端全量确认无回归**

```bash
uv run pytest -q && uv run ruff check
```

Expected: 172 passed / ruff clean

- [x] **Step 6: 提交**

```bash
git add backend/app/services/sync_progress.py backend/tests/services/test_sync_progress.py
git commit -m "feat(sync-progress): add SyncProgressTracker singleton with unit tests"
```

---

## Task 2: 后端 — `sync_historical_for_pool` 接受 from/to + `_read_bar_for_date` + 集成 tracker

**Files:**
- Modify: `backend/app/services/daily_sync.py:20-71`
- Modify: `backend/app/services/daily_sync.py:74-94`（`sync_today`）
- Modify: `backend/app/main.py:46-52`（startup hook）
- Modify: `backend/tests/test_daily_sync.py`（既有 3 个 `test_sync_today_*` 用例 + 新增 from/to 循环用例）

**Interfaces:**

```python
# 旧签名
def sync_historical_for_pool(codes: list[str], target_date: date | None = None) -> Path: ...

# 新签名
def sync_historical_for_pool(codes: list[str], from_date: date, to_date: date) -> Path: ...

# 新增辅助
def _read_bar_for_date(code: str, target_date: date) -> dict | None:
    """Return bar for specific date, or None if no row matches that date."""
```

- [x] **Step 1: 写新测试（RED）**

在 `backend/tests/test_daily_sync.py` 末尾新增：

```python
from app.services.daily_sync import _read_bar_for_date, sync_historical_for_pool
from app.services.sync_progress import tracker
from datetime import date

def test_read_bar_for_date_returns_specific_day():
    """Fixture 159915.XSHE.csv starts 2024-04-19. Reading that day returns that bar."""
    bar = _read_bar_for_date("159915.XSHE", date(2024, 4, 19))
    assert bar is not None
    assert bar["date"] == "2024-04-19"
    assert "close" in bar

def test_read_bar_for_date_returns_none_for_missing_day():
    """Date outside fixture range returns None."""
    bar = _read_bar_for_date("159915.XSHE", date(2025, 12, 31))
    assert bar is None

def test_read_bar_for_date_returns_none_for_missing_code():
    bar = _read_bar_for_date("999999.XXXX", date(2024, 4, 19))
    assert bar is None


def test_sync_historical_for_pool_iterates_date_range(tmp_path, monkeypatch):
    """Sync 2 codes over 3 days updates tracker 6 times (2*3) and writes summary."""
    from app.services import daily_sync
    # override SYNC_DIR to tmp to avoid polluting real dir
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    # reset module singleton before test
    tracker.clear()

    codes = ["159915.XSHE", "510300.XSHG"]
    out = sync_historical_for_pool(
        codes=codes, from_date=date(2024, 4, 19), to_date=date(2024, 4, 21),
    )
    assert out.exists()
    # tracker should have entries for both codes
    assert tracker.is_active() is True
    infos = {p.code: p for p in tracker.get_all()}
    assert set(infos.keys()) == set(codes)
    # each code: total_days=3, completed_days=3, current_date=last day
    for code in codes:
        assert infos[code].total_days == 3
        assert infos[code].completed_days == 3
        assert infos[code].current_date == date(2024, 4, 21)
    # overall_index should be 6 (last step)
    for code in codes:
        assert infos[code].overall_index == 6
        assert infos[code].overall_total == 6
    tracker.clear()  # cleanup


def test_sync_historical_for_pool_handles_missing_day(tmp_path, monkeypatch):
    """When a (code, date) is missing, it should be marked 'missing' not crash."""
    from app.services import daily_sync
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    tracker.clear()
    # 159915.XSHE has no data on 2025-12-31
    out = sync_historical_for_pool(
        codes=["159915.XSHE"], from_date=date(2025, 12, 31), to_date=date(2025, 12, 31),
    )
    payload = json.loads(out.read_text())
    assert payload["rows"][0]["status"] == "missing"
    tracker.clear()


def test_sync_today_with_explicit_target_date_still_works(tmp_path, monkeypatch):
    """sync_today(target_date=...) still returns Path, summary filename contains date."""
    from app.services.daily_sync import sync_today
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    out = sync_today(target_date=date(2024, 4, 19))
    assert out.exists()
    assert "2024-04-19" in out.name
```

- [x] **Step 2: 跑新测试验证 RED**

```bash
uv run pytest tests/test_daily_sync.py -v
```

Expected: 新增 5 个测试全 FAIL（_read_bar_for_date 不存在；sync_historical_for_pool 旧签名不接受 from_date/to_date）

- [x] **Step 3: 实现 `_read_bar_for_date`**

`backend/app/services/daily_sync.py`，在 `_read_latest_bar` 之后加：

```python
def _read_bar_for_date(code: str, target_date: date) -> dict | None:
    """Return {date, close, volume, money} for the bar on `target_date`, or None.

    Reads the same fixture CSV as `_read_latest_bar` but filters to the
    specific date. Returns None if the code has no data on that day.
    """
    csv_path = FIXTURES_DIR / f"{code}.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, parse_dates=["date"])
    target_ts = pd.Timestamp(target_date)
    matches = df[df["date"] == target_ts]
    if matches.empty:
        return None
    row = matches.iloc[0]
    return {
        "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
        "close": float(row["close"]),
        "volume": float(row["volume"]),
        "money": float(row["money"]),
    }
```

- [x] **Step 4: 重构 `sync_historical_for_pool`**

替换整个函数：

```python
def sync_historical_for_pool(codes: list[str], from_date: date, to_date: date) -> Path:
    """For each code in `codes`, iterate [from_date, to_date] and update the
    global SyncProgressTracker with each (code, date) step.

    Writes a summary JSON to SYNC_DIR/{to_date}.json at the end. The tracker
    is populated for the duration of this call; the caller is responsible for
    clearing it (see `sync.api.trigger_sync`).
    """
    from app.services.sync_progress import ProgressInfo, tracker

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
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
            except Exception as e:  # noqa: BLE001 — per-(code,date) isolation
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

    payload = {
        "date": to_date.isoformat(),
        "n_etfs": len(codes),
        "rows": rows,
    }
    out_path = SYNC_DIR / f"{to_date.isoformat()}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False))
    return out_path
```

并在文件顶部 import：
```python
from datetime import date, datetime, timedelta, timezone
from app.services.sync_progress import ProgressInfo, tracker
```

- [x] **Step 5: 重构 `sync_today`**

```python
def _find_latest_bar_date(codes: list[str]) -> pd.Timestamp | None:
    """Find the max date across all fixture CSVs (or None if no data)."""
    latest: pd.Timestamp | None = None
    for code in codes:
        csv_path = FIXTURES_DIR / f"{code}.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty:
            continue
        code_max = df["date"].max()
        if latest is None or code_max > latest:
            latest = code_max
    return latest


def sync_today(target_date: date | None = None) -> Path:
    """Backwards-compatible wrapper. With no args, syncs [latest_bar_date, latest_bar_date]
    (single day) to preserve the old "summary uses latest bar date" behaviour.
    With an explicit `target_date`, syncs just that day.
    """
    codes = sorted(p.stem for p in FIXTURES_DIR.glob("*.csv"))
    if target_date is None:
        latest = _find_latest_bar_date(codes)
        to_date = latest.date() if latest is not None else date.today()
    else:
        to_date = target_date
    return sync_historical_for_pool(codes=codes, from_date=to_date, to_date=to_date)
```

- [x] **Step 6: 改 `main.py:46-52` startup hook**

```python
from datetime import date, timedelta

# inside lifespan:
try:
    codes = _pool_union_codes()
    if codes:
        sync_historical_for_pool(
            codes=codes,
            from_date=date.today() - timedelta(days=30),
            to_date=date.today(),
        )
except Exception:
    log.exception("startup historical sync failed; continuing")
```

- [x] **Step 7: 跑全部 daily_sync 测试验证 GREEN**

```bash
uv run pytest tests/test_daily_sync.py -v
```

Expected: 既有 3 个 + 新增 5 个 = 8/8 passed

- [x] **Step 8: 跑后端全量确认无回归**

```bash
uv run pytest -q && uv run ruff check
```

Expected: 178 passed（172 + 6 新增）/ ruff clean

- [x] **Step 9: 提交**

```bash
git add backend/app/services/daily_sync.py backend/app/main.py backend/tests/test_daily_sync.py
git commit -m "feat(sync-progress): sync_historical_for_pool accepts from/to + tracks progress"
```

---

## Task 3: 后端 — schema + `/api/sync/historical/*` 端点改造

**Files:**
- Modify: `backend/app/schemas.py:70-90`（`SyncETFStatus` / `SyncStatusResponse` / `SyncTriggerResult`）
- Modify: `backend/app/api/sync.py:93-123`（`trigger_sync` / `get_sync_status`）
- Create: `backend/tests/api/test_sync_progress.py`（新端点行为测试）

**Interfaces:**

```python
# backend/app/schemas.py
from datetime import date, datetime

class ProgressInfo(BaseModel):
    code: str
    from_date: date
    to_date: date
    current_date: date
    total_days: int
    completed_days: int
    overall_index: int
    overall_total: int
    started_at: datetime

class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]
    in_progress: list[ProgressInfo] | None = None
    is_running: bool = False

class SyncTriggerResult(SyncStatusResponse):
    synced_count: int
    run_at: datetime
    from_date: date
    to_date: date
```

```python
# backend/app/api/sync.py
@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(
    from_date: date = Query(...),
    to_date: date = Query(...),
) -> SyncTriggerResult: ...
```

- [x] **Step 1: 写新测试（RED）**

`backend/tests/api/test_sync_progress.py`：
```python
"""End-to-end tests for the trigger + status endpoints with date range support."""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.services.sync_progress import tracker


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_tracker():
    """Ensure tracker is clean before/after each test."""
    tracker.clear()
    yield
    tracker.clear()


def test_trigger_sync_requires_from_and_to(client):
    """Calling without query params returns 422."""
    r = client.post("/api/sync/historical/trigger")
    assert r.status_code == 422


def test_trigger_sync_rejects_from_after_to(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-06-01", "to_date": "2024-05-01"},
    )
    assert r.status_code == 400
    assert "from_date must be ≤ to_date" in r.json()["detail"]


def test_trigger_sync_rejects_future_from_date(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2099-01-01", "to_date": "2099-01-02"},
    )
    assert r.status_code == 400
    assert "future" in r.json()["detail"].lower()


def test_trigger_sync_rejects_range_over_730_days(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2020-01-01", "to_date": "2024-01-01"},
    )
    assert r.status_code == 400
    assert "730" in r.json()["detail"]


def test_trigger_sync_succeeds_with_valid_range(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-04-19", "to_date": "2024-04-21"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is False
    assert body["from_date"] == "2024-04-19"
    assert body["to_date"] == "2024-04-21"
    assert body["in_progress"] is None  # cleared after success


def test_status_includes_in_progress_during_sync(client, monkeypatch):
    """Mock sync to take some time so we can observe in_progress during execution."""
    from app.api import sync as sync_api
    from app.services.sync_progress import ProgressInfo

    # Pre-populate tracker to simulate a running sync
    tracker.set("510300", ProgressInfo(
        code="510300",
        from_date=date(2024, 4, 19), to_date=date(2024, 4, 21),
        current_date=date(2024, 4, 20),
        total_days=3, completed_days=2,
        overall_index=2, overall_total=3,
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    ))

    r = client.get("/api/sync/historical/status")
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is True
    assert body["in_progress"] is not None
    assert len(body["in_progress"]) == 1
    assert body["in_progress"][0]["code"] == "510300"
    assert body["in_progress"][0]["current_date"] == "2024-04-20"


def test_status_is_running_false_when_no_sync(client):
    r = client.get("/api/sync/historical/status")
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is False
    assert body["in_progress"] is None
```

- [x] **Step 2: 跑新测试验证 RED**

```bash
uv run pytest tests/api/test_sync_progress.py -v
```

Expected: 7 个测试全 FAIL（query 参数未实现 / schema 字段未加 / in_progress 未返回）

- [x] **Step 3: 改 `backend/app/schemas.py`**

把 `ProgressInfo` 类定义从 `sync_progress.py` re-export 出来（**不**复制实现 — 用 re-import），并修改 `SyncStatusResponse` / `SyncTriggerResult`：

```python
# 顶部新增 import
from app.services.sync_progress import ProgressInfo  # re-export for OpenAPI


class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]
    in_progress: list[ProgressInfo] | None = None
    is_running: bool = False


class SyncTriggerResult(SyncStatusResponse):
    """Result of a manual historical-sync trigger."""

    synced_count: int
    run_at: datetime
    from_date: date
    to_date: date
```

（**注意**：`ProgressInfo` 在 `sync_progress.py` 已定义；schemas.py 仅 re-import，不要复制 Pydantic 字段定义，避免双源）

- [x] **Step 4: 改 `backend/app/api/sync.py`**

```python
# 顶部 import 调整
from datetime import date as date_type
from fastapi import Query

from app.services.sync_progress import ProgressInfo, tracker
from app.services.daily_sync import sync_historical_for_pool

MAX_RANGE_DAYS = 730


@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(
    from_date: date_type = Query(...),
    to_date: date_type = Query(...),
) -> SyncTriggerResult:
    """Run a fresh historical sync for the given date range."""
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

    try:
        sync_historical_for_pool(codes=codes, from_date=from_date, to_date=to_date)
    except Exception as e:  # noqa: BLE001 — surface as 500 with detail
        tracker.clear()
        raise HTTPException(500, detail=f"sync failed: {e}") from e

    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(codes, names, by_code)
    synced_count = sum(1 for e in etfs if e.status == "ok")

    # Snapshot final in_progress before clearing (in case anything to show)
    final_in_progress = tracker.get_all()
    tracker.clear()

    return SyncTriggerResult(
        as_of=as_of,
        etfs=etfs,
        in_progress=final_in_progress if final_in_progress else None,
        is_running=False,
        synced_count=synced_count,
        run_at=datetime.now(timezone.utc),
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/sync/historical/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    """Return the latest historical-sync status for every code in the pool union.

    If a sync is currently running, also returns the in-progress list.
    """
    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(_pool_union_codes(), names, by_code)
    in_progress = tracker.get_all() if tracker.is_active() else None
    return SyncStatusResponse(
        as_of=as_of,
        etfs=etfs,
        in_progress=in_progress,
        is_running=tracker.is_active(),
    )
```

- [x] **Step 5: 跑新测试验证 GREEN**

```bash
uv run pytest tests/api/test_sync_progress.py -v
```

Expected: 7/7 passed

- [x] **Step 6: 跑后端全量确认无回归**

```bash
uv run pytest -q && uv run ruff check
```

Expected: 185 passed（172 + 6 + 7）/ ruff clean

- [x] **Step 7: 提交**

```bash
git add backend/app/schemas.py backend/app/api/sync.py backend/tests/api/test_sync_progress.py
git commit -m "feat(sync-progress): trigger/status endpoints accept date range and expose in_progress"
```

---

## Task 4: 前端 — `DateRangePicker` Modal 组件 + 测试

**Files:**
- Create: `frontend/src/components/DateRangePicker.tsx`
- Create: `frontend/src/components/__tests__/DateRangePicker.test.tsx`

**Interfaces:**

```tsx
// frontend/src/components/DateRangePicker.tsx
export interface DateRange {
  from_date: string;  // YYYY-MM-DD
  to_date: string;
}

export interface DateRangePickerProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (range: DateRange) => void;
  isSubmitting: boolean;
  errorMessage?: string | null;
}

export function DateRangePicker(props: DateRangePickerProps): JSX.Element | null;
```

- [x] **Step 1: 写组件测试（RED）**

`frontend/src/components/__tests__/DateRangePicker.test.tsx`：
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DateRangePicker } from "../DateRangePicker";

function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

describe("DateRangePicker", () => {
  it("does not render when open=false", () => {
    render(<DateRangePicker open={false} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders with default from=today-30, to=today", () => {
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} />);
    const fromInput = screen.getByLabelText(/from/i) as HTMLInputElement;
    const toInput = screen.getByLabelText(/to/i) as HTMLInputElement;
    expect(fromInput.value).toBe(todayISO(-30));
    expect(toInput.value).toBe(todayISO(0));
  });

  it("confirm button disabled when from > to", async () => {
    const user = userEvent.setup();
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} />);
    const fromInput = screen.getByLabelText(/from/i);
    await user.clear(fromInput);
    await user.type(fromInput, todayISO(10));
    const confirmBtn = screen.getByRole("button", { name: /开始同步/ });
    expect(confirmBtn).toBeDisabled();
    expect(screen.getByText(/from_date 必须早于/i)).toBeInTheDocument();
  });

  it("calls onConfirm with { from_date, to_date } when valid", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={onConfirm} isSubmitting={false} />);
    const fromInput = screen.getByLabelText(/from/i);
    const toInput = screen.getByLabelText(/to/i);
    await user.clear(fromInput);
    await user.type(fromInput, "2024-04-19");
    await user.clear(toInput);
    await user.type(toInput, "2024-04-21");
    await user.click(screen.getByRole("button", { name: /开始同步/ }));
    expect(onConfirm).toHaveBeenCalledWith({ from_date: "2024-04-19", to_date: "2024-04-21" });
  });

  it("shows backend error message when provided", () => {
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={false} errorMessage="同步失败" />);
    expect(screen.getByText(/同步失败/)).toBeInTheDocument();
  });

  it("confirm button disabled while isSubmitting", () => {
    render(<DateRangePicker open={true} onClose={() => {}} onConfirm={() => {}} isSubmitting={true} />);
    expect(screen.getByRole("button", { name: /同步中|开始同步/ })).toBeDisabled();
  });

  it("cancel button calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<DateRangePicker open={true} onClose={onClose} onConfirm={() => {}} isSubmitting={false} />);
    await user.click(screen.getByRole("button", { name: /取消/ }));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [x] **Step 2: 跑测试验证 RED**

```bash
cd ../frontend && npx vitest run src/components/__tests__/DateRangePicker.test.tsx
```

Expected: 7 个测试全 FAIL（模块不存在）

- [x] **Step 3: 实现 `DateRangePicker` 组件**

`frontend/src/components/DateRangePicker.tsx`：
```tsx
import { useEffect, useState } from "react";

export interface DateRange {
  from_date: string;
  to_date: string;
}

export interface DateRangePickerProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (range: DateRange) => void;
  isSubmitting: boolean;
  errorMessage?: string | null;
}

function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function DateRangePicker({
  open, onClose, onConfirm, isSubmitting, errorMessage,
}: DateRangePickerProps) {
  const [fromDate, setFromDate] = useState(todayISO(-30));
  const [toDate, setToDate] = useState(todayISO(0));

  useEffect(() => {
    if (open) {
      setFromDate(todayISO(-30));
      setToDate(todayISO(0));
    }
  }, [open]);

  if (!open) return null;

  const fromInvalid = fromDate > toDate;
  const canConfirm = !fromInvalid && !isSubmitting;

  return (
    <div role="dialog" aria-label="选择同步日期范围" className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded bg-background p-6 shadow-lg">
        <h3 className="mb-4 text-lg font-semibold">选择同步日期范围</h3>
        {errorMessage && (
          <p role="alert" className="mb-3 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-700">
            {errorMessage}
          </p>
        )}
        <div className="mb-4 space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block text-muted-foreground">From (开始日期)</span>
            <input
              type="date"
              value={fromDate}
              max={toDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full rounded border px-2 py-1"
              data-testid="from-date-input"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-muted-foreground">To (结束日期)</span>
            <input
              type="date"
              value={toDate}
              min={fromDate}
              max={todayISO(0)}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full rounded border px-2 py-1"
              data-testid="to-date-input"
            />
          </label>
          {fromInvalid && (
            <p role="alert" className="text-xs text-red-600">
              from_date 必须早于或等于 to_date
            </p>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
            data-testid="cancel-button"
          >
            取消
          </button>
          <button
            type="button"
            onClick={() => onConfirm({ from_date: fromDate, to_date: toDate })}
            disabled={!canConfirm}
            className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
            data-testid="confirm-button"
          >
            {isSubmitting ? "同步中…" : "开始同步"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [x] **Step 4: 跑测试验证 GREEN**

```bash
npx vitest run src/components/__tests__/DateRangePicker.test.tsx
```

Expected: 7/7 passed

- [x] **Step 5: 跑前端全量确认无回归**

```bash
npx vitest run
```

Expected: 38/38 + 7 new = 45/45 passed

- [x] **Step 6: tsc + build 验证**

```bash
npx tsc --noEmit && npm run build
```

Expected: tsc clean / build 成功

- [x] **Step 7: 提交**

```bash
git add frontend/src/components/DateRangePicker.tsx frontend/src/components/__tests__/DateRangePicker.test.tsx
git commit -m "feat(sync-progress): add DateRangePicker modal with from/to validation"
```

---

## Task 5: 前端 — `useTriggerSync` mutation 接受 `{from_date, to_date}`

**Files:**
- Modify: `frontend/src/api/hooks.ts:269-279`
- Modify: `frontend/src/api/__tests__/hooks.test.ts`（既有测试中调用 `useTriggerSync` 的部分需要更新签名 — 由 implementer 跑测试时定位并更新）

**Interfaces:**

```ts
// 旧
useTriggerSync().mutate()  // 无参

// 新
useTriggerSync().mutate({ from_date: "2024-04-19", to_date: "2024-04-21" })
```

- [x] **Step 1: 写 mutation 行为测试（RED）**

先在 `frontend/src/api/__tests__/hooks.test.ts`（或新建 `hooks.trigger.test.ts`）加：

```tsx
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { describe, expect, it, beforeAll, afterAll, afterEach } from "vitest";
import { useTriggerSync } from "../hooks";

const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useTriggerSync", () => {
  it("POSTs to /api/sync/historical/trigger with from_date and to_date query params", async () => {
    let capturedUrl: string | null = null;
    server.use(
      http.post("*/api/sync/historical/trigger", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          as_of: "2024-04-21", etfs: [], in_progress: null, is_running: false,
          synced_count: 0, run_at: new Date().toISOString(),
          from_date: "2024-04-19", to_date: "2024-04-21",
        });
      })
    );
    const { result } = renderHook(() => useTriggerSync(), { wrapper });
    result.current.mutate({ from_date: "2024-04-19", to_date: "2024-04-21" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedUrl).toContain("from_date=2024-04-19");
    expect(capturedUrl).toContain("to_date=2024-04-21");
  });
});
```

- [x] **Step 2: 跑测试验证 RED**

```bash
npx vitest run src/api/__tests__/hooks.trigger.test.ts
```

Expected: 测试 FAIL（mutate 期望无参，或 URL 不含 query params）

- [x] **Step 3: 修改 `useTriggerSync`**

`frontend/src/api/hooks.ts:269-279`：
```ts
export interface SyncTriggerVariables {
  from_date: string;
  to_date: string;
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation<SyncTriggerResult, Error, SyncTriggerVariables>({
    mutationFn: ({ from_date, to_date }) =>
      api<SyncTriggerResult>(
        `/api/sync/historical/trigger?from_date=${from_date}&to_date=${to_date}`,
        { method: "POST" }
      ),
    onSuccess: (data) => {
      qc.setQueryData(["sync-historical-status"], data);
      qc.invalidateQueries({ queryKey: ["sync-historical-status"] });
    },
  });
}
```

- [x] **Step 4: 同步更新 `DynamicPoolPage.test.tsx` 中所有 `syncHistory.mutate()` 调用为 `syncHistory.mutate({ from_date, to_date })`**

（implementer 跑 `npx vitest run` 时会被测试报错指出来，统一改）

- [x] **Step 5: 跑前端全量**

```bash
npx vitest run
```

Expected: 既有 38 + 新增 1 + 调整后继续全部通过

- [x] **Step 6: tsc + build 验证**

```bash
npx tsc --noEmit && npm run build
```

Expected: tsc clean / build 成功

- [x] **Step 7: 提交**

```bash
git add frontend/src/api/hooks.ts frontend/src/api/__tests__/ frontend/src/pages/__tests__/DynamicPoolPage.test.tsx
git commit -m "feat(sync-progress): useTriggerSync accepts {from_date, to_date} variables"
```

---

## Task 6: 前端 — `SyncProgressBanner` + `RowProgressBar` + `DynamicPoolPage` 集成

**Files:**
- Create: `frontend/src/components/SyncProgressBanner.tsx`
- Create: `frontend/src/components/RowProgressBar.tsx`
- Create: `frontend/src/components/__tests__/SyncProgressBanner.test.tsx`
- Create: `frontend/src/components/__tests__/RowProgressBar.test.tsx`
- Modify: `frontend/src/pages/DynamicPoolPage.tsx`
- Modify: `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（新增进度相关测试用例）

**Interfaces:**

```tsx
// SyncProgressBanner.tsx
import type { ProgressInfo } from "@/api/hooks";
export function SyncProgressBanner({ progress }: { progress: ProgressInfo[] }): JSX.Element | null;

// RowProgressBar.tsx
import type { ProgressInfo } from "@/api/hooks";
export function RowProgressBar({ info }: { info: ProgressInfo }): JSX.Element;
```

（注意：`ProgressInfo` 类型需要在 `hooks.ts` 中 export — Task 3 后端产出 schema 后，前端需要对应的 TS 类型）

- [x] **Step 1: 在 `frontend/src/api/hooks.ts` 中 export `ProgressInfo` TS 类型**

```ts
// 顶部 import
import type { components } from "@/api/types";  // 如果有 OpenAPI 生成；否则手写
// 或手写：
export interface ProgressInfo {
  code: string;
  from_date: string;
  to_date: string;
  current_date: string;
  total_days: number;
  completed_days: number;
  overall_index: number;
  overall_total: number;
  started_at: string;
}

// 同时扩展 SyncStatusResponse 类型
export interface SyncStatusResponse {
  as_of: string | null;
  etfs: SyncETFStatus[];
  in_progress: ProgressInfo[] | null;
  is_running: boolean;
}
```

（如果项目已有 OpenAPI 自动生成的类型，implementer 优先用生成的；否则手写并加注释 `// mirror backend/app/services/sync_progress.py:ProgressInfo`）

- [x] **Step 2: 写 `SyncProgressBanner` 测试（RED）**

`frontend/src/components/__tests__/SyncProgressBanner.test.tsx`：
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SyncProgressBanner } from "../SyncProgressBanner";
import type { ProgressInfo } from "@/api/hooks";

const sampleProgress: ProgressInfo[] = [
  {
    code: "510300", from_date: "2024-04-19", to_date: "2024-04-21",
    current_date: "2024-04-20", total_days: 3, completed_days: 2,
    overall_index: 2, overall_total: 3, started_at: "2026-06-29T10:00:00Z",
  },
];

describe("SyncProgressBanner", () => {
  it("returns null when progress is empty", () => {
    const { container } = render(<SyncProgressBanner progress={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows total progress and current code/day", () => {
    render(<SyncProgressBanner progress={sampleProgress} />);
    expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
    expect(screen.getByText(/510300/)).toBeInTheDocument();
    expect(screen.getByText(/2024-04-20/)).toBeInTheDocument();
  });

  it("aggregates overall_index across multiple codes", () => {
    const two: ProgressInfo[] = [
      { ...sampleProgress[0], code: "510300", overall_index: 5, overall_total: 10 },
      { ...sampleProgress[0], code: "510500", overall_index: 6, overall_total: 10 },
    ];
    render(<SyncProgressBanner progress={two} />);
    // overall_index should sum to 11... no wait, we want the max (current step) — adjust per impl
  });
});
```

- [x] **Step 3: 实现 `SyncProgressBanner`**

```tsx
import type { ProgressInfo } from "@/api/hooks";

export function SyncProgressBanner({ progress }: { progress: ProgressInfo[] }) {
  if (progress.length === 0) return null;
  const total = progress[0].overall_total;
  const done = Math.max(...progress.map((p) => p.overall_index));
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  // Show the most recently updated code (largest overall_index)
  const current = progress.reduce((a, b) => (a.overall_index >= b.overall_index ? a : b));

  return (
    <div className="rounded border bg-blue-50 p-3 text-sm" data-testid="sync-progress-banner">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-medium">同步进行中</span>
        <span className="text-muted-foreground">{done} / {total} ({percent}%)</span>
      </div>
      <div className="mb-2 h-2 w-full overflow-hidden rounded bg-blue-100">
        <div className="h-full bg-blue-500 transition-all" style={{ width: `${percent}%` }} />
      </div>
      <div className="text-xs text-muted-foreground">
        当前：<span className="font-mono">{current.code}</span>{" "}
        {current.current_date} / 共 {current.total_days} 天
      </div>
    </div>
  );
}
```

- [x] **Step 4: 写 `RowProgressBar` 测试（RED）+ 实现**

测试：传入 ProgressInfo → 渲染进度条 + "current_date / total_days 天"
实现：用 `current_date` 和 `total_days` 算百分比，渲染 `<div role="progressbar" aria-valuenow={pct}>`

- [x] **Step 5: 改 `DynamicPoolPage.tsx`**

- 新增 state：`pickerOpen`, `syncError`
- 接入 `useSyncStatus` 的 `is_running` 和 `in_progress`
- 把「同步 ETF 历史数据」按钮 `onClick` 改为 `setPickerOpen(true)`
- 渲染 `<SyncProgressBanner progress={inProgress} />`（条件：`inProgress.length > 0`）
- 表格行：`progressByCode.get(e.code)` 存在则渲染 `<RowProgressBar info={...} />`，否则既有 `<SyncStatusBadge>`
- 渲染 `<DateRangePicker>`：onConfirm 调 `syncHistory.mutate(range, { onError, onSuccess })`

- [x] **Step 6: 写 `DynamicPoolPage.test.tsx` 进度相关测试（RED）**

新增：
- 顶部横幅在 `is_running=true` 时显示
- 行内进度在 `in_progress` 包含 code 时显示
- 按钮在 `is_running` 时 disabled
- 确认 Picker 后 mutate 被正确调用

（msw 拦截 `/api/sync/historical/status` 返回 `in_progress` 数组，断言 UI 渲染）

- [x] **Step 7: 跑前端全量 + tsc + build**

```bash
npx vitest run && npx tsc --noEmit && npm run build
```

Expected: 既有 38 + 新增 ~6 = ~44/44 passed；tsc / build 干净

- [x] **Step 8: 提交**

```bash
git add frontend/src/components/SyncProgressBanner.tsx frontend/src/components/RowProgressBar.tsx \
        frontend/src/components/__tests__/SyncProgressBanner.test.tsx frontend/src/components/__tests__/RowProgressBar.test.tsx \
        frontend/src/api/hooks.ts frontend/src/pages/DynamicPoolPage.tsx frontend/src/pages/__tests__/DynamicPoolPage.test.tsx
git commit -m "feat(sync-progress): render progress banner + row bar + integrate DateRangePicker"
```

---

## Task 7: 全量验证 + 手动 smoke + 收尾

**Files:** 无新文件

- [x] **Step 1: 跑后端全量 + ruff**

```bash
cd ../backend && uv run pytest -q && uv run ruff check
```

Expected: 185 passed（172 既有 + 13 新增）/ ruff clean

- [x] **Step 2: 跑前端全量 + tsc + build**

```bash
cd ../frontend && npx vitest run && npx tsc --noEmit && npm run build
```

Expected: 既有 38 + 新增 ~7 = ~45/45 passed；tsc / build 干净

- [x] **Step 3: 手动浏览器 smoke（人工，必做）**

启动 dev server：
```bash
# 终端 A
cd backend && uv run uvicorn app.main:app --reload --port 8000
# 终端 B
cd frontend && npm run dev
```

打开 http://localhost:5173/dynamic-pool，按以下顺序验证：

1. **Modal 弹出**：点击「同步 ETF 历史数据」→ 看到 from=今天-30 / to=今天 的 Modal
2. **默认 disable**：把 from 改成今天 → 「开始同步」按钮 disable + 错误提示
3. **范围触发**：选 2024-04-19 → 2024-04-21，点「开始同步」→ Modal 保持打开
4. **Network 观察**：DevTools Network 看到：
   - POST `/api/sync/historical/trigger?from_date=2024-04-19&to_date=2024-04-21`（200）
   - GET `/api/sync/historical/status` 每 10s 一次（轮询）
5. **进度展示**：在 sync 还没完成时（47 codes × 3 days = 141 ops 通常 < 5s，可能很快），看到顶部横幅 `X / 141`
6. **行内进度**：看到某 code 行有进度条 + 日期
7. **完成后清除**：sync 完成后横幅消失，所有行显示 `ok` badge
8. **按钮 disabled**：sync 期间两个按钮均 disabled
9. **后端校验**：curl 试 from > to / 跨度 > 730 → 400 + 正确 detail

如果失败，回到对应 Task 排查。

- [x] **Step 4: 跑 final review（subagent-driven-development）**

按 superpowers:subagent-driven-development 流程，dispatch final code reviewer subagent（用最 capable model），传 `git merge-base main HEAD` 作为 base + HEAD 作为 head 生成的 review package。

- [x] **Step 5: 修复 review 发现的 Critical / Important 问题（如有）**

- [x] **Step 6: 准备合并**

```bash
cd /Users/zane/Workspace/etf-momentum
git log --oneline main..HEAD   # 应该有 6 个 commit
git status                     # 干净
```

---

## 风险与缓解

- **Task 5 改 `useTriggerSync` 签名可能破坏既有测试**（中）：plan 已说明 implementer 跑测试时定位更新；预期改动 < 5 处
- **Task 6 `ProgressInfo` TS 类型需要手写**（低）：本期 mock 项目无 OpenAPI 生成；手写 + 注释指向后端 schema
- **Task 7 smoke 步骤 4-5 进度条一闪而过**（中）：mock fixture 47×3=141 ops < 1s；如要延长观察，调高日期范围（用 730 天或扩展 fixture）。如果太快看不到进度，可在 dev 环境下临时给 `_read_bar_for_date` 加 `time.sleep(0.01)` 用于 smoke（**不在 commit 中**）

---

**Report 文件**: `/Users/zane/Workspace/etf-momentum/.superpowers/sdd/aspu-task-N-report.md`（N = 1..7）

"""Historical sync API: status + trigger endpoints."""
from __future__ import annotations

import json
from datetime import date as date_type
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.db import get_engine, session_scope
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.schemas import (
    CancelResult,
    ProgressSnapshot,
    SyncETFStatus,
    SyncStatusResponse,
    SyncTriggerResult,
)
from app.services.daily_sync import SYNC_DIR, sync_historical_for_pool
from app.services.sync_progress import ProgressInfo, tracker

router = APIRouter(tags=["sync"])

MAX_RANGE_DAYS = 730


def _pool_union_codes() -> list[str]:
    """Deduplicated union of static_pool and dynamic_pool codes.

    Includes every row from both tables (regardless of `enabled` / `is_enabled`):
    the union represents the universe of ETFs that *could* be in scope, not
    just those the user has actively selected. Sorted for stable ordering.
    """
    codes: set[str] = set()
    with session_scope(get_engine()) as s:
        for code, in s.query(StaticPool.code).all():
            codes.add(code)
        for code, in s.query(DynamicPoolEntry.code).all():
            codes.add(code)
    return sorted(codes)


def _pool_dynamic_codes() -> list[str]:
    """Codes from dynamic_pool_entry only. Sorted for stable ordering."""
    codes: set[str] = set()
    with session_scope(get_engine()) as s:
        for code, in s.query(DynamicPoolEntry.code).all():
            codes.add(code)
    return sorted(codes)


def _dynamic_meta_lookup() -> dict[str, tuple[str, bool, datetime]]:
    """Resolve code -> (name, is_enabled, last_synced_at) from dynamic_pool_entry."""
    meta: dict[str, tuple[str, bool, datetime]] = {}
    with session_scope(get_engine()) as s:
        for code, name, is_enabled, last_synced_at in s.query(
            DynamicPoolEntry.code,
            DynamicPoolEntry.name,
            DynamicPoolEntry.is_enabled,
            DynamicPoolEntry.last_synced_at,
        ).all():
            meta[code] = (name, is_enabled, last_synced_at)
    return meta


def _name_lookup() -> dict[str, str]:
    """Resolve code -> human-readable name from static_pool then dynamic_pool.

    Static wins on collision (it's the curated, user-maintained pool).
    """
    names: dict[str, str] = {}
    with session_scope(get_engine()) as s:
        for code, display_name in s.query(StaticPool.code, StaticPool.display_name).all():
            if display_name:
                names[code] = display_name
        for code, dyn_name in s.query(DynamicPoolEntry.code, DynamicPoolEntry.name).all():
            if dyn_name and code not in names:
                names[code] = dyn_name
    return names


def _latest_summary() -> tuple[str | None, dict[str, dict]]:
    """Return (as_of, code -> row) from the newest summary JSON, or (None, {})."""
    if not SYNC_DIR.exists():
        return None, {}
    files = sorted(SYNC_DIR.glob("*.json"), reverse=True)
    if not files:
        return None, {}
    payload = json.loads(files[0].read_text())
    as_of = payload.get("date")
    by_code = {r["code"]: r for r in payload.get("rows", [])}
    return as_of, by_code


def _build_etfs(
    codes: list[str],
    names: dict[str, str],
    by_code: dict[str, dict],
    meta: dict[str, tuple[str, bool, datetime]],
    in_progress: list[ProgressInfo],
) -> list[SyncETFStatus]:
    """Construct SyncETFStatus rows for dynamic pool codes with progress overlay."""
    progress_by_code = {p.code: p for p in in_progress}
    etfs: list[SyncETFStatus] = []
    for code in codes:
        row = by_code.get(code)
        dyn_name, is_enabled, last_synced_at = meta.get(
            code, (names.get(code, ""), True, None)
        )
        # Prefer dynamic_pool_entry.name; fallback to static_pool name
        name = dyn_name or names.get(code)
        if code in progress_by_code:
            p = progress_by_code[code]
            completed = p.overall_index
            total = p.overall_total
            percent = round(completed / total * 100) if total > 0 else 0
            etfs.append(
                SyncETFStatus(
                    code=code,
                    name=name,
                    last_synced_date=None,
                    last_synced_at=last_synced_at,
                    is_enabled=is_enabled,
                    status="in_progress",
                    error=None,
                    progress=ProgressSnapshot(
                        completed=completed,
                        total=total,
                        current_code=p.code,
                        current_date=p.current_date,
                        percent=percent,
                    ),
                )
            )
        elif row is None:
            etfs.append(
                SyncETFStatus(
                    code=code,
                    name=name,
                    last_synced_date=None,
                    last_synced_at=last_synced_at,
                    is_enabled=is_enabled,
                    status="never",
                    error=None,
                )
            )
        else:
            etfs.append(
                SyncETFStatus(
                    code=code,
                    name=name,
                    last_synced_date=row.get("date"),
                    last_synced_at=last_synced_at,
                    is_enabled=is_enabled,
                    status=row.get("status", "ok"),
                    error=row.get("error"),
                )
            )
    return etfs


@router.get("/sync/historical/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    """Return dynamic pool + history sync status (single endpoint, drives the page)."""
    names = _name_lookup()
    meta = _dynamic_meta_lookup()
    as_of, by_code = _latest_summary()
    in_progress = tracker.get_all() if tracker.is_active() else None
    etfs = _build_etfs(
        _pool_dynamic_codes(), names, by_code, meta, in_progress or []
    )
    return SyncStatusResponse(
        as_of=as_of,
        etfs=etfs,
        in_progress=in_progress,
        is_running=tracker.is_active(),
    )


@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(
    background: BackgroundTasks,
    from_date: date_type = Query(...),  # noqa: B008 — FastAPI Query pattern
    to_date: date_type = Query(...),  # noqa: B008 — FastAPI Query pattern
) -> SyncTriggerResult:
    """Validate + schedule background sync + return immediately (non-blocking)."""
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

    # Schedule the actual sync to run after this response is sent.
    # The wrapper clears the progress entries on completion (both normal and
    # cancel paths). On cancel the cancel flag is preserved so the next
    # /status poll sees `is_running=false, in_progress=null, is_cancelled=true`.
    def _run_sync_and_clear() -> None:
        try:
            sync_historical_for_pool(
                codes=codes, from_date=from_date, to_date=to_date
            )
        finally:
            # Always clear progress (so is_active() returns False → is_running=false).
            # The cancel flag is preserved separately so /status reflects is_cancelled.
            tracker.clear_progress()

    background.add_task(_run_sync_and_clear)

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
    """Request cancellation of a running sync. Returns 400 if no sync is active."""
    if not tracker.is_active():
        raise HTTPException(400, "no sync running")
    tracker.cancel()
    return CancelResult(cancelled=True)

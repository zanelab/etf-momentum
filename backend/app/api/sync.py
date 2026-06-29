"""Historical sync API: status + trigger endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db import get_engine, session_scope
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.schemas import SyncETFStatus, SyncStatusResponse, SyncTriggerResult
from app.services.daily_sync import SYNC_DIR, sync_historical_for_pool

router = APIRouter(tags=["sync"])


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
    codes: list[str], names: dict[str, str], by_code: dict[str, dict]
) -> list[SyncETFStatus]:
    """Construct SyncETFStatus rows for each code, marking missing ones as 'never'."""
    etfs: list[SyncETFStatus] = []
    for code in codes:
        row = by_code.get(code)
        if row is None:
            etfs.append(
                SyncETFStatus(
                    code=code,
                    name=names.get(code),
                    last_synced_date=None,
                    status="never",
                    error=None,
                )
            )
        else:
            etfs.append(
                SyncETFStatus(
                    code=code,
                    name=names.get(code),
                    last_synced_date=row.get("date"),
                    status=row.get("status", "ok"),
                    error=row.get("error"),
                )
            )
    return etfs


@router.get("/sync/historical/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    """Return the latest historical-sync status for every code in the pool union."""
    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(_pool_union_codes(), names, by_code)
    return SyncStatusResponse(as_of=as_of, etfs=etfs)


@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync() -> SyncTriggerResult:
    """Run a fresh historical sync over the pool union and return its status."""
    codes = _pool_union_codes()
    if not codes:
        raise HTTPException(status_code=400, detail="pool is empty; nothing to sync")
    run_at = datetime.now(timezone.utc)
    try:
        sync_historical_for_pool(codes=codes)
    except Exception as e:  # noqa: BLE001 — surface as 500 with detail
        raise HTTPException(status_code=500, detail=f"sync failed: {e}")

    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(codes, names, by_code)
    synced_count = sum(1 for e in etfs if e.status == "ok")
    return SyncTriggerResult(
        as_of=as_of,
        etfs=etfs,
        synced_count=synced_count,
        run_at=run_at,
    )
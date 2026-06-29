"""Mock daily close-of-market sync.

In production this would pull the latest OHLCV from a data provider and persist
into a real store. The mock reads each fixture's latest bar and writes a
summary JSON under `backend/data/daily_sync/{YYYY-MM-DD}.json` so callers can
verify the sync ran.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from app.services.sync_progress import ProgressInfo, tracker

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


def sync_historical_for_pool(codes: list[str], from_date: date, to_date: date) -> Path:
    """For each code in `codes`, iterate [from_date, to_date] and update the
    global SyncProgressTracker with each (code, date) step.

    Writes a summary JSON to SYNC_DIR/{to_date}.json at the end. The tracker
    is populated for the duration of this call; the caller is responsible for
    clearing it (see `sync.api.trigger_sync`).
    """
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

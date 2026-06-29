"""Mock daily close-of-market sync.

In production this would pull the latest OHLCV from a data provider and persist
into a real store. The mock reads each fixture's latest bar and writes a
summary JSON under `backend/data/daily_sync/{YYYY-MM-DD}.json` so callers can
verify the sync ran.
"""
from __future__ import annotations

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
    """Backwards-compatible wrapper: sync all fixture codes.

    Preserves the original default behaviour: when ``target_date`` is None, the
    sync file is named after the latest bar date found across all fixtures,
    not ``date.today()``.
    """
    codes = sorted(p.stem for p in FIXTURES_DIR.glob("*.csv"))
    if target_date is None:
        latest: pd.Timestamp | None = None
        for code in codes:
            bar = _read_latest_bar(code)
            if bar is None:
                continue
            ts = pd.Timestamp(bar["date"])
            if latest is None or ts > latest:
                latest = ts
        if latest is None:
            raise RuntimeError(f"No fixture CSVs found under {FIXTURES_DIR}")
        target_date = latest.date()
    return sync_historical_for_pool(codes=codes, target_date=target_date)

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


def sync_today(target_date: date | None = None) -> Path:
    """Write a sync summary file for `target_date` (default: latest in fixtures).

    Returns the path to the written summary.
    """
    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    latest: pd.Timestamp | None = None
    rows: list[dict] = []
    for csv_path in sorted(FIXTURES_DIR.glob("*.csv")):
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty:
            continue
        last = df.iloc[-1]
        ts = pd.Timestamp(last["date"])
        if latest is None or ts > latest:
            latest = ts
        rows.append(
            {
                "code": csv_path.stem,
                "date": ts.strftime("%Y-%m-%d"),
                "close": float(last["close"]),
                "volume": float(last["volume"]),
                "money": float(last["money"]),
            }
        )

    if latest is None:
        raise RuntimeError(f"No fixture CSVs found under {FIXTURES_DIR}")

    sync_date = target_date or latest.date()
    payload = {
        "date": sync_date.isoformat(),
        "last_bar_date": latest.strftime("%Y-%m-%d"),
        "n_etfs": len(rows),
        "rows": rows,
    }
    out_path = SYNC_DIR / f"{sync_date.isoformat()}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False))
    return out_path

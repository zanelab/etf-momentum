"""Tests for the mock daily sync."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.services.daily_sync import SYNC_DIR, sync_today


def test_sync_today_writes_summary_file() -> None:
    out = sync_today()
    assert out.exists()
    assert out.parent == SYNC_DIR


def test_sync_today_summary_includes_all_fixtures() -> None:
    out = sync_today()
    import json

    payload = json.loads(out.read_text())
    fixture_count = sum(
        1 for _ in (Path(__file__).resolve().parent.parent / "data" / "fixtures").glob("*.csv")
    )
    assert payload["n_etfs"] == fixture_count
    for row in payload["rows"]:
        assert {"code", "date", "close", "volume", "money"}.issubset(row.keys())


def test_sync_today_honors_explicit_target_date() -> None:
    out = sync_today(target_date=date(2026, 3, 1))
    assert out.name == "2026-03-01.json"

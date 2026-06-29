"""Tests for the mock daily sync."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.services.daily_sync import SYNC_DIR, sync_today


def test_sync_today_writes_summary_file() -> None:
    out = sync_today()
    assert out.exists()
    assert out.parent == SYNC_DIR


def test_sync_today_summary_includes_all_fixtures() -> None:
    out = sync_today()
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


def test_sync_historical_for_pool_writes_per_etf_status() -> None:
    from app.services.daily_sync import sync_historical_for_pool

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


def test_sync_historical_for_pool_records_failed_without_aborting(monkeypatch) -> None:
    """One code's source raises; other code still syncs; failed row has status=failed + error."""
    from app.services import daily_sync

    def fake_read_latest(code: str):
        if code == "510300.XSHG":
            raise RuntimeError("akshare timeout")
        return {"date": "2026-03-19", "close": 3.9, "volume": 1.0, "money": 1.0}

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

    out = sync_historical_for_pool(
        codes=["510300.XSHG", "999999.XSHG"], target_date=date(2026, 3, 1)
    )
    rows = {r["code"]: r for r in json.loads(out.read_text())["rows"]}
    assert rows["510300.XSHG"]["status"] == "ok"
    assert rows["999999.XSHG"]["status"] == "missing"
    assert rows["999999.XSHG"]["close"] is None

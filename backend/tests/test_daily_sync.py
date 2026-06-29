"""Tests for the mock daily sync."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.services import daily_sync
from app.services.daily_sync import (
    SYNC_DIR,
    _read_bar_for_date,
    sync_historical_for_pool,
    sync_today,
)
from app.services.sync_progress import tracker


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


def test_sync_historical_for_pool_writes_per_etf_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)

    codes = ["510300.XSHG", "510500.XSHG"]
    out = sync_historical_for_pool(
        codes=codes, from_date=date(2026, 3, 19), to_date=date(2026, 3, 19)
    )
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

    def fake_read_bar_for_date(code: str, _target_date):
        if code == "510300.XSHG":
            raise RuntimeError("akshare timeout")
        return {"date": "2026-03-19", "close": 3.9, "volume": 1.0, "money": 1.0}

    monkeypatch.setattr(daily_sync, "_read_bar_for_date", fake_read_bar_for_date)

    out = daily_sync.sync_historical_for_pool(
        codes=["510300.XSHG", "510500.XSHG"],
        from_date=date(2026, 3, 19),
        to_date=date(2026, 3, 19),
    )
    rows = {r["code"]: r for r in json.loads(out.read_text())["rows"]}
    assert rows["510300.XSHG"]["status"] == "failed"
    assert "akshare timeout" in rows["510300.XSHG"]["error"]
    assert rows["510500.XSHG"]["status"] == "ok"


def test_sync_historical_for_pool_marks_missing_code(tmp_path, monkeypatch) -> None:
    """A code with no fixture CSV gets status=missing, not failed."""
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    tracker.clear()
    out = sync_historical_for_pool(
        codes=["510300.XSHG", "999999.XSHG"],
        from_date=date(2026, 3, 19),
        to_date=date(2026, 3, 19),
    )
    rows = {r["code"]: r for r in json.loads(out.read_text())["rows"]}
    assert rows["510300.XSHG"]["status"] == "ok"
    assert rows["999999.XSHG"]["status"] == "missing"
    assert rows["999999.XSHG"]["close"] is None
    tracker.clear()


# ---------------------------------------------------------------------------
# Task 2: from/to signature + _read_bar_for_date + tracker integration
# ---------------------------------------------------------------------------


def test_read_bar_for_date_returns_specific_day() -> None:
    """Fixture 159915.XSHE.csv starts 2024-04-19. Reading that day returns that bar."""
    bar = _read_bar_for_date("159915.XSHE", date(2024, 4, 19))
    assert bar is not None
    assert bar["date"] == "2024-04-19"
    assert "close" in bar


def test_read_bar_for_date_returns_none_for_missing_day() -> None:
    """Date outside fixture range returns None."""
    bar = _read_bar_for_date("159915.XSHE", date(2030, 1, 1))
    assert bar is None


def test_read_bar_for_date_returns_none_for_missing_code() -> None:
    bar = _read_bar_for_date("999999.XXXX", date(2024, 4, 19))
    assert bar is None


def test_sync_historical_for_pool_iterates_date_range(tmp_path, monkeypatch) -> None:
    """Sync 2 codes over 3 days updates tracker 6 times (2*3) and writes summary."""
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
        assert infos[code].overall_total == 6
    # code-major iteration: first code ends at step 3, second at step 6
    assert infos["159915.XSHE"].overall_index == 3
    assert infos["510300.XSHG"].overall_index == 6
    tracker.clear()  # cleanup


def test_sync_historical_for_pool_handles_missing_day(tmp_path, monkeypatch) -> None:
    """When a (code, date) is missing, it should be marked 'missing' not crash."""
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    tracker.clear()
    # 159915.XSHE has no data on 2030-01-01
    out = sync_historical_for_pool(
        codes=["159915.XSHE"], from_date=date(2030, 1, 1), to_date=date(2030, 1, 1),
    )
    payload = json.loads(out.read_text())
    assert payload["rows"][0]["status"] == "missing"
    tracker.clear()


def test_sync_today_with_explicit_target_date_still_works(tmp_path, monkeypatch) -> None:
    """sync_today(target_date=...) still returns Path, summary filename contains date."""
    monkeypatch.setattr(daily_sync, "SYNC_DIR", tmp_path)
    out = sync_today(target_date=date(2024, 4, 19))
    assert out.exists()
    assert "2024-04-19" in out.name

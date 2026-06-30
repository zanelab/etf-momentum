"""Tests for the cancel sync endpoint + trigger async behavior."""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.db import init_db
from app.main import app
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.services.sync_progress import ProgressInfo, tracker


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Per-test sqlite DB + tracker isolation so tests don't leak state."""
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    db_module.reset_engine_for_tests()
    init_db()

    # Seed one StaticPool row so trigger has a non-empty pool
    from datetime import datetime as dt
    now = dt.utcnow()
    with db_module.session_scope(db_module.get_engine()) as s:
        s.add(StaticPool(code="510300.XSHG", display_name="沪深300ETF", enabled=True))
        s.add(
            DynamicPoolEntry(
                code="510500.XSHG",
                name="中证500ETF",
                is_enabled=False,
                last_synced_at=now,
            )
        )

    # Ensure tracker is clean before/after each test
    tracker.clear()
    yield
    tracker.clear()
    db_module.reset_engine_for_tests()


@pytest.fixture
def client():
    return TestClient(app)


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

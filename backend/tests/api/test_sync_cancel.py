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


def test_status_after_cancel_reflects_idle_state(client):
    """Cancel 后 status 反映 in_progress 仍非空（cancel 还没传播完成）.

    取消语义：取消请求 → tracker.cancel() → 下次 /status 仍 is_running=true
    因为 _by_code 还在 → 真正的 is_running=false 要等 background task 的
    finally 块执行 tracker.clear_progress()。本测试只断言 cancel 期间状态。
    """
    tracker.set("510300", ProgressInfo(
        code="510300", from_date=date(2024,4,19), to_date=date(2024,4,21),
        current_date=date(2024,4,20), total_days=3, completed_days=2,
        overall_index=2, overall_total=3,
        started_at=datetime.now(timezone.utc),
    ))
    tracker.cancel()
    r = client.get("/api/sync/historical/status")
    body = r.json()
    assert body["is_running"] is True  # _by_code 还在
    assert body["in_progress"] is not None
    assert len(body["in_progress"]) == 1
    # is_cancelled 字段已删除（M17 简化）
    assert "is_cancelled" not in body


def test_status_after_cancelled_sync_returns_is_running_false(client, monkeypatch):
    """End-to-end: background sync 完成后，status 必须报告 is_running=false,
    in_progress=null。is_cancelled 字段已删除（M17 简化）。
    """
    from app.api import sync as sync_api

    def fake_sync(codes, from_date, to_date):
        tracker.set("510300.XSHG", ProgressInfo(
            code="510300.XSHG",
            from_date=from_date, to_date=to_date,
            current_date=from_date, total_days=1, completed_days=0,
            overall_index=1, overall_total=1,
            started_at=datetime.now(timezone.utc),
        ))
        tracker.cancel()
        return None

    monkeypatch.setattr(sync_api, "sync_historical_for_pool", fake_sync)

    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-04-19", "to_date": "2024-04-19"},
    )
    assert r.status_code == 200

    status = client.get("/api/sync/historical/status")
    assert status.status_code == 200
    body = status.json()
    assert body["is_running"] is False
    assert body["in_progress"] is None
    assert "is_cancelled" not in body  # M17 简化

"""End-to-end tests for the trigger + status endpoints with date range support."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.db import init_db
from app.main import app
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.services import daily_sync
from app.services.sync_progress import tracker


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Per-test sqlite DB + isolated SYNC_DIR so pool rows and summary files don't leak."""
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    db_module.reset_engine_for_tests()
    init_db()

    # Redirect SYNC_DIR to a per-test tmp dir so summary JSON writes are isolated
    fake_sync_dir = tmp_path / "daily_sync"
    fake_sync_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(daily_sync, "SYNC_DIR", fake_sync_dir)
    import app.api.sync as sync_api_module
    monkeypatch.setattr(sync_api_module, "SYNC_DIR", fake_sync_dir)

    # Ensure tracker is clean before/after each test
    tracker.clear()
    yield
    tracker.clear()
    db_module.reset_engine_for_tests()


@pytest.fixture
def client():
    return TestClient(app)


def _seed_pool_rows() -> None:
    """Insert one StaticPool row + one DynamicPoolEntry row."""
    from datetime import datetime
    now = datetime.utcnow()
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


def test_trigger_sync_requires_from_and_to(client):
    """Calling without query params returns 422."""
    r = client.post("/api/sync/historical/trigger")
    assert r.status_code == 422


def test_trigger_sync_rejects_from_after_to(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-06-01", "to_date": "2024-05-01"},
    )
    assert r.status_code == 400
    assert "from_date must be ≤ to_date" in r.json()["detail"]


def test_trigger_sync_rejects_future_from_date(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2099-01-01", "to_date": "2099-01-02"},
    )
    assert r.status_code == 400
    assert "future" in r.json()["detail"].lower()


def test_trigger_sync_rejects_range_over_730_days(client):
    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2020-01-01", "to_date": "2024-01-01"},
    )
    assert r.status_code == 400
    assert "730" in r.json()["detail"]


def test_trigger_sync_succeeds_with_valid_range(client, monkeypatch):
    """When pool is seeded and sync is monkeypatched, valid date range triggers a sync.

    BackgroundTasks semantics: trigger returns 200 immediately with
    is_running=True / synced_count=0 / etfs=[]. TestClient waits for
    background tasks to complete before the request returns, so after the
    post() we can assert the side-effects (summary file written, tracker
    cleared) without polling the status endpoint.
    """
    _seed_pool_rows()

    import app.api.sync as sync_api_module

    def fake_sync(codes, from_date, to_date):
        # Write a summary file so _latest_summary finds something
        daily_sync.SYNC_DIR.mkdir(parents=True, exist_ok=True)
        sync_date = to_date.isoformat()
        rows = [
            {"code": code, "date": sync_date, "close": 1.0, "volume": 1.0,
             "money": 1.0, "status": "ok", "error": None}
            for code in codes
        ]
        payload = {"date": sync_date, "n_etfs": len(rows), "rows": rows}
        out = daily_sync.SYNC_DIR / f"{sync_date}.json"
        out.write_text(__import__("json").dumps(payload, ensure_ascii=False))
        return out

    monkeypatch.setattr(sync_api_module, "sync_historical_for_pool", fake_sync)

    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-04-19", "to_date": "2024-04-21"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Trigger response now reflects "scheduled, not yet complete":
    assert body["is_running"] is True
    assert body["synced_count"] == 0
    assert body["etfs"] == []
    assert body["in_progress"] == []
    assert body["from_date"] == "2024-04-19"
    assert body["to_date"] == "2024-04-21"

    # TestClient.post() awaits BackgroundTasks, so the side-effects are
    # observable immediately after the call returns:
    # (a) summary JSON was written by the background sync
    assert (daily_sync.SYNC_DIR / "2024-04-21.json").exists()
    # (b) tracker was cleared by sync_historical_for_pool on normal completion
    assert tracker.is_active() is False
    assert tracker.get_all() == []

    # And the status endpoint reflects the post-sync state:
    s = client.get("/api/sync/historical/status")
    assert s.status_code == 200
    sbody = s.json()
    assert sbody["is_running"] is False
    assert sbody["in_progress"] is None
    assert sbody["as_of"] == "2024-04-21"
    # M17: etfs now returns dynamic pool only (1 entry: 510500.XSHG)
    assert len(sbody["etfs"]) == 1
    assert sbody["etfs"][0]["code"] == "510500.XSHG"
    assert all(e["status"] == "ok" for e in sbody["etfs"])


def test_status_includes_in_progress_during_sync(client):
    """When tracker is pre-populated, status returns in_progress and is_running=True."""
    from datetime import datetime, timezone

    from app.services.sync_progress import ProgressInfo

    # Pre-populate tracker to simulate a running sync
    tracker.set("510300", ProgressInfo(
        code="510300",
        from_date=date(2024, 4, 19), to_date=date(2024, 4, 21),
        current_date=date(2024, 4, 20),
        total_days=3, completed_days=2,
        overall_index=2, overall_total=3,
        started_at=datetime.now(timezone.utc),
    ))

    r = client.get("/api/sync/historical/status")
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is True
    assert body["in_progress"] is not None
    assert len(body["in_progress"]) == 1
    assert body["in_progress"][0]["code"] == "510300"
    assert body["in_progress"][0]["current_date"] == "2024-04-20"


def test_status_is_running_false_when_no_sync(client):
    r = client.get("/api/sync/historical/status")
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is False
    assert body["in_progress"] is None


def test_trigger_sync_rejects_when_already_running(client):
    """When a sync is already in progress (tracker populated), another trigger
    request must be rejected with 400."""
    from datetime import datetime, timezone

    from app.services.sync_progress import ProgressInfo

    # Simulate a running sync by pre-populating the tracker
    tracker.set("510300", ProgressInfo(
        code="510300",
        from_date=date(2024, 4, 19), to_date=date(2024, 4, 21),
        current_date=date(2024, 4, 19),
        total_days=3, completed_days=1,
        overall_index=1, overall_total=3,
        started_at=datetime.now(timezone.utc),
    ))

    r = client.post(
        "/api/sync/historical/trigger",
        params={"from_date": "2024-04-19", "to_date": "2024-04-21"},
    )
    assert r.status_code == 400
    assert "already running" in r.json()["detail"]
    # The existing sync's tracker state must NOT be cleared by the rejected request
    assert tracker.is_active() is True


def test_status_returns_dynamic_pool_only(client):
    """status endpoint /etfs 只包含 dynamic pool（不包含 static_pool）."""
    _seed_pool_rows()
    s = client.get("/api/sync/historical/status")
    assert s.status_code == 200
    body = s.json()
    codes = [e["code"] for e in body["etfs"]]
    assert codes == ["510500.XSHG"]  # only the dynamic one
    assert "510300.XSHG" not in codes  # static excluded


def test_status_etfs_carry_is_enabled_and_last_synced_at(client):
    """每项 etf 包含 is_enabled + last_synced_at 字段."""
    _seed_pool_rows()
    s = client.get("/api/sync/historical/status")
    body = s.json()
    item = body["etfs"][0]
    assert item["code"] == "510500.XSHG"
    assert "is_enabled" in item
    assert item["is_enabled"] is False  # seeded as False
    assert "last_synced_at" in item
    assert item["last_synced_at"] is not None  # seeded with now


def test_status_etfs_carries_progress_for_in_progress_code(client):
    """tracker 中有的 code 在 etfs[] 里以 in_progress 状态出现 + 携带 progress."""
    from datetime import datetime, timezone

    from app.services.sync_progress import ProgressInfo

    _seed_pool_rows()
    tracker.set("510500.XSHG", ProgressInfo(
        code="510500.XSHG",
        from_date=date(2024, 4, 19), to_date=date(2024, 4, 21),
        current_date=date(2024, 4, 20),
        total_days=3, completed_days=2,
        overall_index=2, overall_total=3,
        started_at=datetime.now(timezone.utc),
    ))
    s = client.get("/api/sync/historical/status")
    body = s.json()
    item = next(e for e in body["etfs"] if e["code"] == "510500.XSHG")
    assert item["status"] == "in_progress"
    assert item["progress"] is not None
    assert item["progress"]["completed"] == 2
    assert item["progress"]["total"] == 3
    assert item["progress"]["percent"] == 67  # round(2/3*100)


def test_status_omits_is_cancelled_field(client):
    """响应 schema 不再含 is_cancelled 字段."""
    _seed_pool_rows()
    s = client.get("/api/sync/historical/status")
    body = s.json()
    assert "is_cancelled" not in body

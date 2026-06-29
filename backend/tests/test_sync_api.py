"""Tests for the historical sync API: status and trigger endpoints."""
from __future__ import annotations

import json
from datetime import date as date_type
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.db import init_db
from app.main import app
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.services import daily_sync


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Per-test sqlite DB + isolated SYNC_DIR so pool rows and summary files don't leak."""
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    db_module.reset_engine_for_tests()
    init_db()

    # Redirect SYNC_DIR to a per-test tmp dir so summary JSON writes are isolated
    # (the production SYNC_DIR lives in the repo and is tracked by git).
    fake_sync_dir = tmp_path / "daily_sync"
    fake_sync_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(daily_sync, "SYNC_DIR", fake_sync_dir)
    # The API module imports SYNC_DIR by name; rebind the symbol it sees.
    import app.api.sync as sync_api_module
    monkeypatch.setattr(sync_api_module, "SYNC_DIR", fake_sync_dir)

    yield
    db_module.reset_engine_for_tests()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _seed_pool_rows() -> None:
    """Insert one StaticPool row + one DynamicPoolEntry row, both canonical form."""
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


def _write_summary_file(date_str: str, rows: list[dict]) -> None:
    """Write a fake summary JSON under SYNC_DIR for a given date."""
    daily_sync.SYNC_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"date": date_str, "n_etfs": len(rows), "rows": rows}
    (daily_sync.SYNC_DIR / f"{date_str}.json").write_text(
        json.dumps(payload, ensure_ascii=False)
    )


def test_status_endpoint_returns_pool_union(client: TestClient) -> None:
    """GET /api/sync/historical/status returns one row per pool code, with name resolved.

    Given: static_pool has 510300.XSHG, dynamic_pool has 510500.XSHG, and a
    summary file dated 2026-03-01 lists both rows with status=ok.
    When: GET /api/sync/historical/status
    Then: response.etfs has length 2; each row has code, name (from pool),
          last_synced_date="2026-03-01", status="ok".
    """
    _seed_pool_rows()
    _write_summary_file(
        "2026-03-01",
        [
            {"code": "510300.XSHG", "date": "2026-03-01", "close": 3.9, "volume": 1.0,
             "money": 1.0, "status": "ok", "error": None},
            {"code": "510500.XSHG", "date": "2026-03-01", "close": 5.5, "volume": 2.0,
             "money": 2.0, "status": "ok", "error": None},
        ],
    )

    resp = client.get("/api/sync/historical/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["as_of"] == "2026-03-01"
    assert len(body["etfs"]) == 2

    by_code = {e["code"]: e for e in body["etfs"]}
    assert by_code["510300.XSHG"]["name"] == "沪深300ETF"
    assert by_code["510300.XSHG"]["last_synced_date"] == "2026-03-01"
    assert by_code["510300.XSHG"]["status"] == "ok"
    assert by_code["510500.XSHG"]["name"] == "中证500ETF"
    assert by_code["510500.XSHG"]["last_synced_date"] == "2026-03-01"
    assert by_code["510500.XSHG"]["status"] == "ok"


def test_status_endpoint_marks_codes_not_in_summary_as_never(
    client: TestClient,
) -> None:
    """If the summary file does not list a pool code, that code gets status=never."""
    _seed_pool_rows()
    # Summary only mentions 510300.XSHG; 510500.XSHG is absent → should be 'never'.
    _write_summary_file(
        "2026-03-01",
        [
            {"code": "510300.XSHG", "date": "2026-03-01", "close": 3.9, "volume": 1.0,
             "money": 1.0, "status": "ok", "error": None},
        ],
    )

    resp = client.get("/api/sync/historical/status")
    assert resp.status_code == 200
    body = resp.json()

    by_code = {e["code"]: e for e in body["etfs"]}
    assert by_code["510500.XSHG"]["status"] == "never"
    assert by_code["510500.XSHG"]["last_synced_date"] is None
    assert by_code["510500.XSHG"]["error"] is None
    # 510300.XSHG is still ok
    assert by_code["510300.XSHG"]["status"] == "ok"


def test_trigger_endpoint_runs_sync_and_returns_synced_count(
    client: TestClient, monkeypatch
) -> None:
    """POST /api/sync/historical/trigger calls sync_historical_for_pool and returns synced_count.

    Strategy: monkeypatch sync_historical_for_pool so it writes a controlled
    summary file (mimicking its real behaviour without hitting real fixtures).
    """
    _seed_pool_rows()

    import app.api.sync as sync_api_module

    def fake_sync(codes, target_date=None):  # noqa: ARG001 — match real signature
        sync_date = (target_date or date_type.today()).isoformat()
        daily_sync.SYNC_DIR.mkdir(parents=True, exist_ok=True)
        rows = [
            {"code": code, "date": sync_date, "close": 1.0, "volume": 1.0,
             "money": 1.0, "status": "ok", "error": None}
            for code in codes
        ]
        payload = {"date": sync_date, "n_etfs": len(rows), "rows": rows}
        out = daily_sync.SYNC_DIR / f"{sync_date}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False))
        return out

    # Patch where it's USED (sync_api_module bound it at import time).
    monkeypatch.setattr(sync_api_module, "sync_historical_for_pool", fake_sync)

    resp = client.post("/api/sync/historical/trigger")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["synced_count"] == 2
    assert body["etfs"], "etfs should be non-empty"
    assert all(e["status"] == "ok" for e in body["etfs"])
    # run_at is set and parseable as ISO-8601 with timezone.
    # Pydantic serializes UTC datetimes with a 'Z' suffix; normalize for parsing.
    run_at_str = body["run_at"].replace("Z", "+00:00")
    run_at = datetime.fromisoformat(run_at_str)
    assert run_at.tzinfo is not None
    # And it is in the recent past (within a minute of now)
    now = datetime.now(timezone.utc)
    assert abs((now - run_at).total_seconds()) < 60


def test_trigger_endpoint_returns_500_on_sync_failure(
    client: TestClient, monkeypatch
) -> None:
    """If sync_historical_for_pool raises, the endpoint returns 500."""
    _seed_pool_rows()

    import app.api.sync as sync_api_module

    def boom(codes, target_date=None):  # noqa: ARG001
        raise RuntimeError("akshare timeout")

    # Patch where it's USED (sync_api_module bound it at import time).
    monkeypatch.setattr(sync_api_module, "sync_historical_for_pool", boom)

    resp = client.post("/api/sync/historical/trigger")
    assert resp.status_code == 500
    assert "akshare timeout" in resp.json()["detail"]
"""Tests for dynamic pool endpoints: list, sync, toggle."""
from __future__ import annotations

import sys
import types
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.db import get_engine, init_db, session_scope
from app.main import app
from app.models.dynamic_pool import DynamicPoolEntry


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Use a per-test sqlite DB so dynamic_pool_entry rows don't leak."""
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    from app import db as db_module

    db_module.reset_engine_for_tests()
    init_db()
    yield
    db_module.reset_engine_for_tests()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _client_with_akshare_mocked():
    """Return (client, mock_akshare_module) so tests can configure fund_etf_name_em."""
    if "akshare" not in sys.modules:
        sys.modules["akshare"] = types.ModuleType("akshare")
    return sys.modules["akshare"]


def _inject_fake_akshare(monkeypatch):
    """Install a fake akshare module so AkShareSource can be instantiated
    without the real library installed."""
    fake = types.ModuleType("akshare")
    fake.fund_etf_hist_em = lambda *a, **kw: None
    fake.fund_etf_name_em = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "akshare", fake)
    return fake


def test_list_dynamic_pool_empty(client: TestClient) -> None:
    """Given no rows in dynamic_pool_entry
    When GET /api/configs/pool/dynamic
    Then response is [].
    """
    resp = client.get("/api/configs/pool/dynamic")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_dynamic_pool_returns_rows(client: TestClient) -> None:
    """Given 2 rows in dynamic_pool_entry (one enabled, one disabled)
    When GET /api/configs/pool/dynamic
    Then both rows are returned in code-sorted order.
    """
    now = datetime.utcnow()
    with session_scope(get_engine()) as s:
        s.add(DynamicPoolEntry(code="510300.XSHG", name="沪深300ETF", is_enabled=True, last_synced_at=now))
        s.add(DynamicPoolEntry(code="510500.XSHG", name="中证500ETF", is_enabled=False, last_synced_at=now))
    resp = client.get("/api/configs/pool/dynamic")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["code"] == "510300.XSHG"
    assert body[0]["is_enabled"] is True
    assert body[1]["code"] == "510500.XSHG"
    assert body[1]["is_enabled"] is False


def test_sync_dynamic_pool_inserts_new_rows(client: TestClient, monkeypatch) -> None:
    """Given empty dynamic_pool_entry and akshare returns 3 ETFs
    When POST /api/configs/pool/dynamic/sync is called
    Then 3 rows are inserted, all is_enabled=False, last_synced_at is fresh,
    response has {synced: 3, total: 3, enabled: 0}.
    """
    fake = _inject_fake_akshare(monkeypatch)
    import pandas as pd

    fake.fund_etf_name_em = lambda: pd.DataFrame(
        {"基金代码": ["510300.XSHG", "510500.XSHG", "159915.XSHE"], "基金名称": ["沪深300", "中证500", "创业板"]}
    )
    monkeypatch.setenv("ETF_DATA_SOURCE", "akshare")

    resp = client.post("/api/configs/pool/dynamic/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"synced": 3, "total": 3, "enabled": 0}

    with session_scope(get_engine()) as s:
        rows = list(s.exec(select(DynamicPoolEntry).order_by(DynamicPoolEntry.code)).all())
        assert len(rows) == 3
        assert all(r.is_enabled is False for r in rows)
        assert all(r.last_synced_at is not None for r in rows)


def test_sync_preserves_existing_is_enabled(client: TestClient, monkeypatch) -> None:
    """Given an existing row with is_enabled=True
    When sync runs and akshare still includes that code
    Then the row's is_enabled remains True (sync does not clobber user choice).
    """
    fake = _inject_fake_akshare(monkeypatch)
    import pandas as pd

    now = datetime(2026, 1, 1, 0, 0, 0)
    with session_scope(get_engine()) as s:
        s.add(DynamicPoolEntry(code="510300.XSHG", name="old name", is_enabled=True, last_synced_at=now))
    fake.fund_etf_name_em = lambda: pd.DataFrame(
        {"基金代码": ["510300.XSHG"], "基金名称": ["new name"]}
    )
    monkeypatch.setenv("ETF_DATA_SOURCE", "akshare")

    resp = client.post("/api/configs/pool/dynamic/sync")
    assert resp.status_code == 200
    with session_scope(get_engine()) as s:
        row = s.exec(select(DynamicPoolEntry).where(DynamicPoolEntry.code == "510300.XSHG")).one()
        assert row.is_enabled is True  # preserved
        assert row.name == "new name"  # updated
        assert row.last_synced_at > now  # refreshed


def test_sync_returns_enabled_count(client: TestClient, monkeypatch) -> None:
    """Given 1 enabled + 1 disabled row before sync, and akshare returns both
    When POST /api/configs/pool/dynamic/sync
    Then response enabled=1.
    """
    fake = _inject_fake_akshare(monkeypatch)
    import pandas as pd

    now = datetime.utcnow()
    with session_scope(get_engine()) as s:
        s.add(DynamicPoolEntry(code="A", name="a-old", is_enabled=True, last_synced_at=now))
        s.add(DynamicPoolEntry(code="B", name="b-old", is_enabled=False, last_synced_at=now))
    fake.fund_etf_name_em = lambda: pd.DataFrame(
        {"基金代码": ["A", "B"], "基金名称": ["a-new", "b-new"]}
    )
    monkeypatch.setenv("ETF_DATA_SOURCE", "akshare")

    resp = client.post("/api/configs/pool/dynamic/sync")
    body = resp.json()
    assert body == {"synced": 2, "total": 2, "enabled": 1}


def test_patch_toggles_is_enabled(client: TestClient) -> None:
    """Given an existing row with is_enabled=False
    When PATCH /api/configs/pool/dynamic/{code} with {"is_enabled": true}
    Then response is 200, is_enabled becomes True.
    """
    now = datetime.utcnow()
    with session_scope(get_engine()) as s:
        s.add(DynamicPoolEntry(code="510300.XSHG", name="沪深300", is_enabled=False, last_synced_at=now))

    resp = client.patch("/api/configs/pool/dynamic/510300.XSHG", json={"is_enabled": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "510300.XSHG"
    assert body["is_enabled"] is True

    with session_scope(get_engine()) as s:
        row = s.exec(select(DynamicPoolEntry).where(DynamicPoolEntry.code == "510300.XSHG")).one()
        assert row.is_enabled is True


def test_patch_unknown_code_returns_404(client: TestClient) -> None:
    """When PATCH is called with a code that doesn't exist
    Then response is 404.
    """
    resp = client.patch("/api/configs/pool/dynamic/999999.XSHG", json={"is_enabled": True})
    assert resp.status_code == 404


def test_patch_can_disable(client: TestClient) -> None:
    """Given an enabled row, PATCH with is_enabled=False disables it."""
    now = datetime.utcnow()
    with session_scope(get_engine()) as s:
        s.add(DynamicPoolEntry(code="X", name="x", is_enabled=True, last_synced_at=now))
    resp = client.patch("/api/configs/pool/dynamic/X", json={"is_enabled": False})
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is False


def test_sync_ignores_fixture_default(client: TestClient, monkeypatch) -> None:
    """Even when ETF_DATA_SOURCE=fixture, sync MUST pull from akshare (per
    spec: dynamic pool represents the full universe, not the curated fixture).
    Verifies sync decouples from the global default source.
    """
    import pandas as pd

    # Inject fake akshare so the ak_share branch of make_source can instantiate
    fake = _inject_fake_akshare(monkeypatch)
    fake.fund_etf_name_em = lambda: pd.DataFrame(
        {"基金代码": ["999999.XSHG"], "基金名称": ["全市场ETF"]}
    )
    # Default is fixture; sync should still hit akshare
    monkeypatch.setenv("ETF_DATA_SOURCE", "fixture")
    resp = client.post("/api/configs/pool/dynamic/sync")
    assert resp.status_code == 200
    with session_scope(get_engine()) as s:
        rows = list(s.exec(select(DynamicPoolEntry)).all())
        # Only the akshare-returned row should appear, NOT any fixture CSV code
        assert len(rows) == 1
        assert rows[0].code == "999999.XSHG"
        assert rows[0].name == "全市场ETF"

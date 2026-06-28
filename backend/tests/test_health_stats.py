"""Tests for /api/health cache stats extension."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data_sources import reset_source_cache
from app.data_sources.cache import CachedSource
from app.db import get_engine, init_db, reset_engine_for_tests
from app.main import app


@pytest.fixture(autouse=True)
def _setup(tmp_path, monkeypatch):
    """Per-test DB and reset source cache so each test starts clean."""
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    reset_engine_for_tests()
    init_db()
    reset_source_cache()
    yield
    reset_engine_for_tests()
    reset_source_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_default_returns_no_cache_stats(client: TestClient) -> None:
    """Default GET /api/health (no ?stats=1) MUST NOT include cache fields,
    even when active source is CachedSource. Backwards compatible."""

    # Inject a CachedSource-like marker
    src = CachedSource.__new__(CachedSource)
    src._inner = None
    src._engine = get_engine()
    src._hit_count = 5
    src._miss_count = 3
    reset_source_cache()
    from app.data_sources import _cache

    _cache["fixture"] = src

    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok"}


def test_health_with_stats_returns_cache_counts(client: TestClient, monkeypatch) -> None:
    """Given active source is CachedSource with hit=5, miss=3
    When GET /api/health?stats=1
    Then response MUST include cache_hit=5 and cache_miss=3."""
    from app.data_sources import _cache

    src = CachedSource.__new__(CachedSource)
    src._inner = None
    src._engine = get_engine()
    src._hit_count = 5
    src._miss_count = 3
    _cache["fixture"] = src

    resp = client.get("/api/health?stats=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["cache_hit"] == 5
    assert body["cache_miss"] == 3


def test_health_stats_with_non_cached_source_omits_fields(client: TestClient) -> None:
    """Given active source is FixtureCSVSource (not CachedSource)
    When GET /api/health?stats=1
    Then response MUST NOT include cache_hit/cache_miss."""
    from app.data_sources import _cache
    from app.data_sources.fixture import FixtureCSVSource

    _cache.clear()
    src = FixtureCSVSource(_get_fixtures_dir())
    _cache["fixture"] = src

    resp = client.get("/api/health?stats=1")
    assert resp.status_code == 200
    body = resp.json()
    assert "cache_hit" not in body
    assert "cache_miss" not in body


def _get_fixtures_dir():
    from pathlib import Path
    return Path(__file__).resolve().parents[2] / "data" / "fixtures"

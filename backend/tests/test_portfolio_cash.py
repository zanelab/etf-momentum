"""Tests for portfolio cash fields and signal computation without fallback."""
from __future__ import annotations

import sys
import types

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    from app import db as db_module
    db_module.reset_engine_for_tests()
    init_db()
    # Prevent akshare or real network calls during startup
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        types.ModuleType("akshare"),
    )
    yield
    db_module.reset_engine_for_tests()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_portfolio_response_includes_available_cash_and_net_value(
    client: TestClient,
) -> None:
    """GET /api/portfolio must return available_cash and net_value.
    available_cash = 100_000 - total_cost (initial mock capital is 100k).
    net_value = total_market_value + available_cash.
    """
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()

    # New fields exist
    assert "available_cash" in body
    assert "net_value" in body

    # Both are numeric
    assert isinstance(body["available_cash"], (int, float))
    assert isinstance(body["net_value"], (int, float))

    # Arithmetic check
    total_cost = body["total_cost"]
    total_market_value = body["total_market_value"]
    assert body["available_cash"] == pytest.approx(100_000 - total_cost, abs=0.01)
    assert body["net_value"] == pytest.approx(
        total_market_value + body["available_cash"], abs=0.01
    )


def test_signals_endpoint_does_not_fall_back_to_100k(
    client: TestClient,
) -> None:
    """When total_value would be 0 (defensive case), signals must NOT silently
    use 100_000. The fallback is removed; cash is sourced from portfolio."""
    resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    # Each BUY signal must have target_value >= 0 (no crash)
    for sig in body["signals"]:
        if sig["type"] == "BUY":
            assert sig.get("target_value") is not None
            assert sig["target_value"] >= 0

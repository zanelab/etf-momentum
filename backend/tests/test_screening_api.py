"""Integration tests for the screening, portfolio, and signals API endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Per-test TestClient.

    Per-test isolation matters here because the conftest's `isolated_db`
    fixture rewrites the DB path per test; a module-scoped client would
    outlive its DB file.
    """
    from app.main import app
    from app.seed import seed_if_empty
    from app import db as db_module

    db_module.init_db()
    seed_if_empty()
    with TestClient(app) as c:
        yield c


def test_screening_today_returns_targets(client: TestClient) -> None:
    resp = client.get("/api/screening/today")
    assert resp.status_code == 200
    body = resp.json()
    assert "as_of" in body
    assert "targets" in body
    assert isinstance(body["targets"], list)
    assert len(body["targets"]) > 0


def test_portfolio_returns_holdings_with_market_value_and_pnl(client: TestClient) -> None:
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert "as_of" in body
    assert "holdings" in body
    assert "total_market_value" in body
    assert "total_cost" in body
    assert "total_pnl" in body
    assert len(body["holdings"]) > 0
    for h in body["holdings"]:
        assert {"code", "shares", "cost_price", "current_price",
                "market_value", "pnl"}.issubset(h.keys())


def test_signals_today_returns_sells_buys(client: TestClient) -> None:
    resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    assert "as_of" in body
    assert "signals" in body
    assert isinstance(body["signals"], list)
    for s in body["signals"]:
        assert s["type"] in {"BUY", "SELL"}
        assert "etf" in s
        assert "reason" in s

"""Tests for the market data API endpoints (history + listing)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app import db as db_module
    from app.main import app
    from app.seed import seed_if_empty

    db_module.init_db()
    seed_if_empty()
    with TestClient(app) as c:
        yield c


def test_market_list_returns_etfs_with_codes_and_names(client: TestClient) -> None:
    resp = client.get("/api/market/list")
    assert resp.status_code == 200
    body = resp.json()
    assert "etfs" in body
    assert len(body["etfs"]) > 0
    sample = body["etfs"][0]
    assert {"code", "display_name"}.issubset(sample.keys())


def test_market_history_returns_rows_for_known_etf(client: TestClient) -> None:
    resp = client.get(
        "/api/market/history",
        params={
            "code": "510300.XSHG",
            "start": "2026-01-01",
            "end": "2026-03-01",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "510300.XSHG"
    assert "rows" in body
    assert len(body["rows"]) > 0
    row = body["rows"][0]
    assert {"date", "open", "high", "low", "close", "volume"}.issubset(row.keys())


def test_market_history_supports_field_filter(client: TestClient) -> None:
    resp = client.get(
        "/api/market/history",
        params={
            "code": "510300.XSHG",
            "start": "2026-02-01",
            "end": "2026-02-28",
            "fields": "close,volume",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["fields"] == ["close", "volume"]
    for row in body["rows"]:
        assert set(row.keys()) == {"date", "close", "volume"}


def test_market_history_missing_code_returns_404(client: TestClient) -> None:
    resp = client.get(
        "/api/market/history",
        params={
            "code": "NOPE.XSHG",
            "start": "2026-01-01",
            "end": "2026-03-01",
        },
    )
    assert resp.status_code == 404


def test_market_history_validates_window(client: TestClient) -> None:
    resp = client.get(
        "/api/market/history",
        params={
            "code": "510300.XSHG",
            "start": "2026-03-01",
            "end": "2026-01-01",
        },
    )
    assert resp.status_code == 400

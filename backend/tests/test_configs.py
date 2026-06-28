"""Integration tests for /api/configs endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import db as db_module
from app.main import app


def _client() -> TestClient:
    db_module.init_db()
    return TestClient(app)


def test_health_endpoint() -> None:
    with _client() as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_pool_replace_and_list() -> None:
    with _client() as client:
        payload = {
            "entries": [
                {"code": "510300.XSHG", "display_name": "沪深300", "enabled": True},
                {"code": "510500.XSHG", "display_name": "中证500", "enabled": False},
            ]
        }
        resp = client.post("/api/configs/pool", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        codes = {e["code"] for e in body}
        assert codes == {"510300.XSHG", "510500.XSHG"}

        listing = client.get("/api/configs/pool").json()
        assert len(listing) == 2


def test_pool_update_single_entry() -> None:
    with _client() as client:
        client.post(
            "/api/configs/pool",
            json={"entries": [{"code": "510300.XSHG", "display_name": "x", "enabled": True}]},
        )
        resp = client.put("/api/configs/pool/510300.XSHG", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False


def test_pool_update_unknown_404() -> None:
    with _client() as client:
        resp = client.put("/api/configs/pool/999999.XSHG", json={"enabled": False})
        assert resp.status_code == 404


def test_pool_delete_entry() -> None:
    with _client() as client:
        client.post(
            "/api/configs/pool",
            json={"entries": [{"code": "510300.XSHG", "display_name": "x", "enabled": True}]},
        )
        resp = client.delete("/api/configs/pool/510300.XSHG")
        assert resp.status_code == 204
        listing = client.get("/api/configs/pool").json()
        assert listing == []


def test_themes_replace_and_list() -> None:
    with _client() as client:
        payload = {"themes": {"半导体": ["芯片", "集成电路"], "医药": ["创新药"]}}
        resp = client.put("/api/configs/themes", json=payload)
        assert resp.status_code == 200
        assert resp.json() == payload

        listing = client.get("/api/configs/themes").json()
        assert listing == payload


def test_strategy_get_put_merge() -> None:
    with _client() as client:
        # PUT merges, doesn't replace existing keys
        client.put("/api/configs/strategy", json={"params": {"_merge_test_key": 30}})
        client.put("/api/configs/strategy", json={"params": {"_another_key": 15}})

        final = client.get("/api/configs/strategy").json()
        assert final["params"]["_merge_test_key"] == 30
        assert final["params"]["_another_key"] == 15

        # Pre-existing seeded keys are still there
        assert final["params"]["momentum_days"] == 25


def test_seed_populates_defaults() -> None:
    """When DB is empty, startup seeds all three tables."""
    with _client() as client:
        pool = client.get("/api/configs/pool").json()
        themes = client.get("/api/configs/themes").json()
        strategy = client.get("/api/configs/strategy").json()

        # Pool seeded from main.py defaults
        assert len(pool) > 100
        assert any(e["code"] == "510300.XSHG" for e in pool)

        # Themes seeded with the 18 categories
        assert len(themes["themes"]) >= 17
        assert "半导体" in themes["themes"]

        # Strategy params seeded
        assert strategy["params"]["momentum_days"] == 25
        assert strategy["params"]["ma_short"] == 20
        assert strategy["params"]["defensive_etf"] == "511880.XSHG"


def test_seed_is_idempotent() -> None:
    """Re-running seed doesn't duplicate data."""
    from app.seed import seed_if_empty

    with _client() as client:
        client.get("/api/health")  # triggers lifespan -> seed
        before = len(client.get("/api/configs/pool").json())
        # Manually re-invoke
        seed_if_empty()
        after = len(client.get("/api/configs/pool").json())
        assert before == after
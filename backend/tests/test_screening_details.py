"""Tests for /api/screening/today details endpoint shape (spec §5.3 进阶)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"


@pytest.fixture
def client():
    """Per-test TestClient with isolated DB."""
    from app import db as db_module
    from app.main import app
    from app.seed import seed_if_empty

    db_module.init_db()
    seed_if_empty()
    with TestClient(app) as c:
        yield c


def test_screening_today_returns_details_per_target(client: TestClient) -> None:
    """Each target code must have a matching details entry with numeric metrics."""
    resp = client.get("/api/screening/today")
    assert resp.status_code == 200
    body = resp.json()
    assert "as_of" in body
    assert "targets" in body
    assert "details" in body
    assert isinstance(body["targets"], list)
    assert isinstance(body["details"], list)

    # At least one target on a normal fixture date
    assert len(body["targets"]) > 0
    assert len(body["details"]) == len(body["targets"])

    detail_codes = [d["code"] for d in body["details"]]
    assert detail_codes == body["targets"]

    # Every detail entry has all metric fields, all numeric
    for d in body["details"]:
        assert {"code", "momentum_score", "annual_return", "r2", "volume_ratio"}.issubset(d.keys())
        assert isinstance(d["code"], str)
        assert isinstance(d["momentum_score"], (int, float))
        assert isinstance(d["annual_return"], (int, float))
        assert isinstance(d["r2"], (int, float))
        # volume_ratio may be None when volume check disabled, but is float otherwise
        vr = d["volume_ratio"]
        assert vr is None or isinstance(vr, (int, float))


def test_screening_today_details_metrics_finite(client: TestClient) -> None:
    """Numeric metrics must be finite (not NaN/Inf)."""
    resp = client.get("/api/screening/today")
    assert resp.status_code == 200
    body = resp.json()
    for d in body["details"]:
        import math
        for key in ("momentum_score", "annual_return", "r2"):
            v = d[key]
            assert math.isfinite(v), f"{key} not finite: {v}"
        if d["volume_ratio"] is not None:
            assert math.isfinite(d["volume_ratio"])

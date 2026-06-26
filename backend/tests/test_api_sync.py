"""FastAPI 端到端：/api/v1/sync/etfs 与 /api/v1/sync/prices。"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.data.client import DailyPriceRow, EtfMasterRow, FakeAkshareClient
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.daily_price import DailyPrice
from app.models.etf import ETF


@pytest.fixture()
def client():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture()
def fake_client(monkeypatch):
    """替换 app.api.v1.sync._build_client，返回 FakeAkshareClient。"""
    def _factory(etfs=None, prices=None):
        return FakeAkshareClient(etfs=etfs, prices=prices)
    return _factory


def _row(d: date, close: str = "4.0") -> DailyPriceRow:
    return DailyPriceRow(
        date=d,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=100,
    )


# ---------------------------------------------------------------------------
# /sync/etfs
# ---------------------------------------------------------------------------


def test_post_sync_etfs(client, monkeypatch):
    c, TestSessionLocal = client

    fake = FakeAkshareClient(
        etfs=[
            EtfMasterRow(code="510300", name="沪深300", market="SH", category="指数"),
            EtfMasterRow(code="510500", name="中证500", market="SH", category="指数"),
        ]
    )
    # Patch the builder in the sync module
    from app.api.v1 import sync as sync_module
    monkeypatch.setattr(sync_module, "_build_client", lambda: fake)

    response = c.post("/api/v1/sync/etfs")
    assert response.status_code == 200
    body = response.json()
    assert body["upserted"] == 2
    assert body["fetched"] == 2

    # DB 里有 2 条
    with TestSessionLocal() as db:
        assert db.query(ETF).count() == 2


def test_post_sync_etfs_idempotent(client, monkeypatch):
    """二次同步 upserted 数应等于 fetched（都是 2，upsert 覆盖）。"""
    c, TestSessionLocal = client

    fake = FakeAkshareClient(
        etfs=[
            EtfMasterRow(code="510300", name="沪深300", market="SH", category="指数"),
        ]
    )
    from app.api.v1 import sync as sync_module
    monkeypatch.setattr(sync_module, "_build_client", lambda: fake)

    c.post("/api/v1/sync/etfs")
    r2 = c.post("/api/v1/sync/etfs")
    body = r2.json()
    assert body["upserted"] == 1  # 仍然被 upsert
    assert body["fetched"] == 1


# ---------------------------------------------------------------------------
# /sync/prices
# ---------------------------------------------------------------------------


def test_post_sync_prices_with_codes(client, monkeypatch):
    c, TestSessionLocal = client
    # 先 seed ETF 主数据
    with TestSessionLocal() as db:
        db.add(ETF(code="510300", name="X", market="SH"))

    fake = FakeAkshareClient(
        prices={
            "510300": [_row(date(2024, 1, d)) for d in (1, 2, 3)],
        }
    )
    from app.api.v1 import sync as sync_module
    monkeypatch.setattr(sync_module, "_build_client", lambda: fake)

    response = c.post(
        "/api/v1/sync/prices",
        json={"codes": ["510300"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] == 1
    assert body["succeeded"] == 1
    assert body["failed"] == 0
    assert body["rows_written"] == 3

    with TestSessionLocal() as db:
        assert db.query(DailyPrice).count() == 3


def test_post_sync_prices_with_date_range(client, monkeypatch):
    c, TestSessionLocal = client
    with TestSessionLocal() as db:
        db.add(ETF(code="510300", name="X", market="SH"))

    fake = FakeAkshareClient(
        prices={
            "510300": [_row(date(2024, 1, d)) for d in range(1, 11)],
        }
    )
    from app.api.v1 import sync as sync_module
    monkeypatch.setattr(sync_module, "_build_client", lambda: fake)

    response = c.post(
        "/api/v1/sync/prices",
        json={
            "codes": ["510300"],
            "start": "2024-01-03",
            "end": "2024-01-07",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows_written"] == 5  # 3,4,5,6,7

    with TestSessionLocal() as db:
        assert db.query(DailyPrice).count() == 5


def test_post_sync_prices_partial_failure(client, monkeypatch):
    """3 只 ETF，1 只 akshare 返回空 → 仍 200，failed=1, succeeded=2。"""
    c, TestSessionLocal = client
    with TestSessionLocal() as db:
        db.add(ETF(code="510300", name="X", market="SH"))
        db.add(ETF(code="510500", name="X", market="SH"))
        db.add(ETF(code="511010", name="X", market="SH"))

    fake = FakeAkshareClient(
        prices={
            "510300": [_row(date(2024, 1, 1))],
            "510500": [_row(date(2024, 1, 1))],
            # 511010 不在 dict 中 → 抛错（FakeAkshareClient 实际返回 []）
        }
    )
    # 让 511010 抛错
    from app.data import client as client_module

    real_fetch = client_module.FakeAkshareClient.fetch_etf_hist

    def boom(self, code, start, end):
        if code == "511010":
            raise RuntimeError("akshare timeout")
        return real_fetch(self, code, start, end)

    monkeypatch.setattr(
        client_module.FakeAkshareClient, "fetch_etf_hist", boom
    )

    from app.api.v1 import sync as sync_module
    monkeypatch.setattr(sync_module, "_build_client", lambda: fake)

    response = c.post(
        "/api/v1/sync/prices",
        json={"codes": ["510300", "510500", "511010"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] == 3
    assert body["succeeded"] == 2
    assert body["failed"] == 1


def test_post_sync_prices_empty_codes_422(client):
    c, _ = client
    response = c.post("/api/v1/sync/prices", json={"codes": []})
    assert response.status_code == 422

"""FastAPI 端到端：/api/v1/etfs 4 个端点（list/detail/prices/count）。"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def _seed_etfs(session_factory, etfs: list[ETF]) -> None:
    with session_factory() as db:
        for e in etfs:
            db.add(e)
        db.commit()


def _seed_prices(session_factory, code: str, dates: list[date]) -> None:
    with session_factory() as db:
        for d in dates:
            db.add(
                DailyPrice(
                    code=code,
                    date=d,
                    open=Decimal("4.0"),
                    high=Decimal("4.2"),
                    low=Decimal("3.9"),
                    close=Decimal("4.0"),
                    volume=1000,
                )
            )
        db.commit()


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


def test_etfs_count_smoke(client):
    c, TestSessionLocal = client
    response = c.get("/api/v1/etfs/count")
    assert response.status_code == 200
    assert response.json() == {"count": 0}

    _seed_etfs(TestSessionLocal, [ETF(code="510300", name="沪深300", market="SH")])
    response = c.get("/api/v1/etfs/count")
    assert response.json() == {"count": 1}


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_etfs_empty(client):
    c, _ = client
    response = c.get("/api/v1/etfs")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_list_etfs_pagination(client):
    c, TestSessionLocal = client
    etfs = [
        ETF(code=f"{i:06d}", name=f"ETF{i}", market="SH", category="指数")
        for i in range(120)
    ]
    _seed_etfs(TestSessionLocal, etfs)

    response = c.get("/api/v1/etfs?limit=50&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 120
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 50
    assert body["items"][0]["code"] == "000000"

    response = c.get("/api/v1/etfs?limit=50&offset=100")
    body = response.json()
    assert body["offset"] == 100
    assert len(body["items"]) == 20


def test_list_etfs_category_filter(client):
    c, TestSessionLocal = client
    _seed_etfs(
        TestSessionLocal,
        [
            ETF(code="510300", name="沪深300", market="SH", category="指数"),
            ETF(code="510500", name="中证500", market="SH", category="指数"),
            ETF(code="511010", name="国债ETF", market="SH", category="债券"),
        ],
    )
    response = c.get("/api/v1/etfs?category=指数")
    body = response.json()
    assert body["total"] == 2
    assert all(item["category"] == "指数" for item in body["items"])


def test_list_etfs_limit_clamp(client):
    c, _ = client
    response = c.get("/api/v1/etfs?limit=1000")
    body = response.json()
    assert body["limit"] == 500


def test_list_etfs_offset_clamp(client):
    c, _ = client
    response = c.get("/api/v1/etfs?offset=-5")
    body = response.json()
    assert body["offset"] == 0


# ---------------------------------------------------------------------------
# detail
# ---------------------------------------------------------------------------


def test_get_etf_detail(client):
    c, TestSessionLocal = client
    _seed_etfs(
        TestSessionLocal,
        [ETF(code="510300", name="沪深300ETF", market="SH", category="指数")],
    )
    response = c.get("/api/v1/etfs/510300")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "510300"
    assert body["name"] == "沪深300ETF"
    assert body["category"] == "指数"


def test_get_etf_not_found_404(client):
    c, _ = client
    response = c.get("/api/v1/etfs/999999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# prices
# ---------------------------------------------------------------------------


def test_get_etf_prices_date_range(client):
    c, TestSessionLocal = client
    _seed_etfs(TestSessionLocal, [ETF(code="510300", name="X", market="SH")])
    dates = [date(2024, 1, d) for d in range(1, 11)]
    _seed_prices(TestSessionLocal, "510300", dates)

    response = c.get(
        "/api/v1/etfs/510300/prices?start=2024-01-03&end=2024-01-08&limit=500"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 6
    # 升序
    assert body[0]["date"] == "2024-01-03"
    assert body[-1]["date"] == "2024-01-08"
    # close 是 string
    assert body[0]["close"] == "4.0000"


def test_get_etf_prices_default_limit(client):
    """不传 limit 时默认 500。"""
    c, TestSessionLocal = client
    _seed_etfs(TestSessionLocal, [ETF(code="510300", name="X", market="SH")])
    # 600 天
    dates = [date(2022, 1, 1) + _days_offset(i) for i in range(600)]
    _seed_prices(TestSessionLocal, "510300", dates)

    response = c.get("/api/v1/etfs/510300/prices")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 500


def test_get_etf_prices_etf_not_found(client):
    c, _ = client
    response = c.get("/api/v1/etfs/999999/prices")
    assert response.status_code == 404


def _days_offset(n: int) -> "timedelta":
    from datetime import timedelta

    return timedelta(days=n)

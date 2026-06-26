"""FastAPI 端到端：/api/v1/backtest 4 个端点。"""

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backtest.engine import BacktestParams, RebalanceFrequency, run_backtest
from app.backtest.persistence import save_backtest_run
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.backtest_run import BacktestRun
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
    yield TestClient(app), TestSessionLocal, eng
    app.dependency_overrides.clear()


def _seed_daily_prices(
    session_factory,
    code: str,
    start: date,
    n: int,
    growth_per_day: Decimal = Decimal("0.001"),
) -> None:
    """每天 close 上涨 growth_per_day，跨度 300+ 天。"""
    with session_factory() as db:
        # ETF 必须存在
        db.add(ETF(code=code, name=code, market="SH", category="指数"))
        for i in range(n):
            d = start + timedelta(days=i)
            close = Decimal("1.0") + growth_per_day * i
            db.add(
                DailyPrice(
                    code=code,
                    date=d,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=1000,
                )
            )
        db.commit()


# ---------------------------------------------------------------------------
# POST /backtest
# ---------------------------------------------------------------------------


def test_post_backtest_happy_path(client):
    c, TestSessionLocal, _ = client
    start = date(2024, 1, 1)
    # 300+ 天；lookback=60+skip=5+start~end=180 → 需要 ~245 天
    for code in ("510300", "510500", "511010"):
        _seed_daily_prices(TestSessionLocal, code, start, 300, Decimal("0.002"))

    body = {
        "etf_pool": ["510300", "510500", "511010"],
        "start": "2024-04-01",
        "end": "2024-09-30",
        "initial_cash": "100000",
        "lookback": 60,
        "skip": 5,
        "top_n": 2,
        "rebalance_freq": "monthly",
    }
    response = c.post("/api/v1/backtest", json=body)
    assert response.status_code == 200, response.text
    out = response.json()
    assert "id" in out
    assert out["momentum_window"] == 60
    assert out["rebalance_freq"] == "monthly"
    assert out["etf_pool"] == ["510300", "510500", "511010"]
    assert out["start_date"] == "2024-04-01"
    assert out["end_date"] == "2024-09-30"
    # metrics 字典：Decimal → str
    assert out["metrics"] is not None
    assert "total_return" in out["metrics"]
    assert isinstance(out["metrics"]["total_return"], str)


def test_post_backtest_empty_pool_422(client):
    c, _, _ = client
    body = {
        "etf_pool": [],
        "start": "2024-01-01",
        "end": "2024-06-30",
        "initial_cash": "100000",
    }
    response = c.post("/api/v1/backtest", json=body)
    assert response.status_code == 422


def test_post_backtest_start_after_end_422(client):
    c, _, _ = client
    body = {
        "etf_pool": ["510300"],
        "start": "2024-12-31",
        "end": "2024-01-01",
        "initial_cash": "100000",
    }
    response = c.post("/api/v1/backtest", json=body)
    assert response.status_code == 422


def test_post_backtest_missing_price_history_422(client):
    c, TestSessionLocal, _ = client
    # 没有 seed → daily_prices 空
    with TestSessionLocal() as db:
        db.add(ETF(code="510300", name="X", market="SH"))

    body = {
        "etf_pool": ["510300"],
        "start": "2024-01-01",
        "end": "2024-06-30",
        "initial_cash": "100000",
    }
    response = c.post("/api/v1/backtest", json=body)
    # 422 由我们抛出，detail 包含 missing code
    assert response.status_code == 422
    assert "510300" in response.json()["detail"]


def test_post_backtest_partial_history_422(client):
    """3 只 ETF 中 1 只没有历史。"""
    c, TestSessionLocal, _ = client
    start = date(2024, 1, 1)
    for code in ("510300", "510500"):
        _seed_daily_prices(TestSessionLocal, code, start, 300, Decimal("0.002"))
    # 511010 不 seed
    with TestSessionLocal() as db:
        db.add(ETF(code="511010", name="X", market="SH"))

    body = {
        "etf_pool": ["510300", "510500", "511010"],
        "start": "2024-04-01",
        "end": "2024-09-30",
        "initial_cash": "100000",
        "lookback": 60,
        "skip": 5,
    }
    response = c.post("/api/v1/backtest", json=body)
    assert response.status_code == 422
    assert "511010" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /backtest
# ---------------------------------------------------------------------------


def test_get_backtest_list(client):
    c, TestSessionLocal, _ = client
    # seed 几个 BacktestRun（用 ORM 直接插）
    for i in range(3):
        run = BacktestRun(
            etf_pool=["510300"],
            momentum_window=252,
            rebalance_freq="monthly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            metrics={"total_return": "0.1"},
        )
        with TestSessionLocal() as db:
            db.add(run)
            db.commit()

    response = c.get("/api/v1/backtest")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_get_backtest_list_pagination(client):
    c, TestSessionLocal, _ = client
    for _ in range(30):
        with TestSessionLocal() as db:
            db.add(
                BacktestRun(
                    etf_pool=["510300"],
                    momentum_window=252,
                    rebalance_freq="monthly",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 6, 30),
                )
            )
            db.commit()
    response = c.get("/api/v1/backtest?limit=10&offset=0")
    body = response.json()
    assert body["total"] == 30
    assert len(body["items"]) == 10
    response = c.get("/api/v1/backtest?limit=10&offset=25")
    body = response.json()
    assert len(body["items"]) == 5


# ---------------------------------------------------------------------------
# GET /backtest/{id}
# ---------------------------------------------------------------------------


def test_get_backtest_detail(client):
    c, TestSessionLocal, _ = client
    with TestSessionLocal() as db:
        run = BacktestRun(
            etf_pool=["510300", "510500"],
            momentum_window=252,
            rebalance_freq="monthly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            metrics={
                "total_return": "0.2",
                "annualized_return": "0.4",
                "max_drawdown": "0.1",
                "sharpe_ratio": "1.5",
            },
        )
        db.add(run)
        db.commit()
        run_id = run.id

    response = c.get(f"/api/v1/backtest/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["etf_pool"] == ["510300", "510500"]
    # Decimal 字段已转 string
    assert body["metrics"]["total_return"] == "0.2"
    assert body["metrics"]["sharpe_ratio"] == "1.5"


def test_get_backtest_detail_404(client):
    c, _, _ = client
    response = c.get("/api/v1/backtest/999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /backtest/{id}/nav
# ---------------------------------------------------------------------------


def test_get_backtest_nav_404(client):
    c, _, _ = client
    response = c.get("/api/v1/backtest/999/nav")
    assert response.status_code == 404


def test_get_backtest_nav_empty(client):
    """BacktestRun 没有 nav 数据（没真正跑过）→ 空 series。"""
    c, TestSessionLocal, _ = client
    with TestSessionLocal() as db:
        run = BacktestRun(
            etf_pool=["510300"],
            momentum_window=252,
            rebalance_freq="monthly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )
        db.add(run)
        db.commit()
        run_id = run.id

    response = c.get(f"/api/v1/backtest/{run_id}/nav")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["nav_series"] == []


def test_post_backtest_then_get_nav(client):
    """POST /backtest 后 nav_series 被持久化，GET /nav 能拿到。"""
    c, TestSessionLocal, _ = client
    start = date(2024, 1, 1)
    for code in ("510300", "510500", "511010"):
        _seed_daily_prices(TestSessionLocal, code, start, 300, Decimal("0.002"))

    body = {
        "etf_pool": ["510300", "510500", "511010"],
        "start": "2024-04-01",
        "end": "2024-09-30",
        "initial_cash": "100000",
        "lookback": 60,
        "skip": 5,
        "top_n": 2,
        "rebalance_freq": "monthly",
    }
    post = c.post("/api/v1/backtest", json=body)
    assert post.status_code == 200
    run_id = post.json()["id"]

    nav = c.get(f"/api/v1/backtest/{run_id}/nav")
    assert nav.status_code == 200
    nav_body = nav.json()
    assert nav_body["id"] == run_id
    assert len(nav_body["nav_series"]) > 0
    # 第一条和最后一条的 nav 是 string
    first = nav_body["nav_series"][0]
    last = nav_body["nav_series"][-1]
    assert isinstance(first["nav"], str)
    assert isinstance(last["nav"], str)
    # 升序
    assert first["date"] <= last["date"]

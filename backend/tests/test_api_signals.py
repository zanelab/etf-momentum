"""FastAPI 端到端：/api/v1/signals 与 /api/v1/signals/latest。"""

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
from app.models.signal_snapshot import SignalSnapshot


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


def _seed_snapshots(session_factory, date_, rows: list[tuple[str, str, int, str]]) -> None:
    """rows = [(etf_code, score_str_or_None, rank_or_-1, action)]"""
    with session_factory() as db:
        for code, score_str, rank, action in rows:
            score = None if score_str is None else Decimal(score_str)
            db.add(
                SignalSnapshot(
                    date=date_,
                    etf_code=code,
                    momentum_score=score,
                    rank=None if rank < 0 else rank,
                    action=action,
                )
            )
        db.commit()


# ---------------------------------------------------------------------------
# /signals/latest 与 /signals
# ---------------------------------------------------------------------------


def test_signals_by_date(client):
    c, TestSessionLocal = client
    _seed_snapshots(
        TestSessionLocal,
        date(2024, 12, 31),
        [
            ("510300", "0.123456", 1, "BUY"),
            ("510500", "0.100000", 2, "BUY"),
            ("511010", None, -1, "WATCH"),
        ],
    )
    response = c.get("/api/v1/signals?date=2024-12-31")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2024-12-31"
    assert len(body["rows"]) == 3
    # score 是 string
    assert body["rows"][0]["momentum_score"] == "0.123456"
    assert body["rows"][0]["action"] == "BUY"
    assert body["rows"][2]["momentum_score"] is None
    assert body["rows"][2]["action"] == "WATCH"


def test_signals_by_date_empty(client):
    c, _ = client
    response = c.get("/api/v1/signals?date=2024-12-31")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2024-12-31"
    assert body["rows"] == []


def test_signals_no_date_returns_latest(client):
    """不传 date → DB MAX(date) 的 snapshot。"""
    c, TestSessionLocal = client
    _seed_snapshots(
        TestSessionLocal,
        date(2024, 12, 30),
        [("510300", "0.05", 1, "BUY")],
    )
    _seed_snapshots(
        TestSessionLocal,
        date(2024, 12, 31),
        [
            ("510300", "0.10", 1, "BUY"),
            ("510500", "0.08", 2, "BUY"),
        ],
    )
    response = c.get("/api/v1/signals")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2024-12-31"
    assert len(body["rows"]) == 2


def test_signals_explicit_latest(client):
    c, TestSessionLocal = client
    _seed_snapshots(
        TestSessionLocal,
        date(2024, 12, 30),
        [("510300", "0.05", 1, "BUY")],
    )
    _seed_snapshots(
        TestSessionLocal,
        date(2024, 12, 31),
        [("510300", "0.10", 1, "BUY")],
    )
    response = c.get("/api/v1/signals/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2024-12-31"
    assert len(body["rows"]) == 1


def test_signals_latest_no_data(client):
    """DB 无 snapshot 时 latest 返回空 rows。"""
    c, _ = client
    response = c.get("/api/v1/signals/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] is None
    assert body["rows"] == []


def test_signals_no_data_no_date(client):
    """DB 无 snapshot 且不传 date → 200 + 空。"""
    c, _ = client
    response = c.get("/api/v1/signals")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] is None
    assert body["rows"] == []


def test_signals_rows_sorted_by_rank(client):
    """rows 按 rank 升序，None 排最后。"""
    c, TestSessionLocal = client
    _seed_snapshots(
        TestSessionLocal,
        date(2024, 12, 31),
        [
            ("510500", "0.08", 2, "BUY"),
            ("999999", None, -1, "WATCH"),
            ("510300", "0.10", 1, "BUY"),
        ],
    )
    response = c.get("/api/v1/signals?date=2024-12-31")
    body = response.json()
    codes = [r["etf_code"] for r in body["rows"]]
    assert codes == ["510300", "510500", "999999"]

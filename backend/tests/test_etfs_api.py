"""FastAPI 端到端：/api/v1/etfs/count 通过 Depends 拿 Session。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.etf import ETF


@pytest.fixture()
def client():
    """用内存 SQLite 替换默认 engine；etf_momentum.db 不被命中。"""
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


def test_etfs_count_returns_zero_on_empty_db(client):
    c, _ = client
    response = c.get("/api/v1/etfs/count")
    assert response.status_code == 200
    assert response.json() == {"count": 0}


def test_etfs_count_reflects_inserted_rows(client):
    c, TestSessionLocal = client
    # 通过 override 路径新增数据
    with TestSessionLocal() as db:
        db.add(ETF(code="510300", name="沪深300ETF", market="SH"))
        db.commit()

    response = c.get("/api/v1/etfs/count")
    assert response.status_code == 200
    assert response.json() == {"count": 1}

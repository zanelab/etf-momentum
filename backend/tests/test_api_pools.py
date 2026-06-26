"""FastAPI 端到端：/api/v1/pools 5 个端点。"""

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
    """内存 SQLite + FastAPI TestClient + 3 只 seed ETF。"""
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

    with TestSessionLocal() as db:
        db.add(ETF(code="510300", name="沪深300ETF", market="SH", category="宽基"))
        db.add(ETF(code="510500", name="中证500ETF", market="SH", category="宽基"))
        db.add(ETF(code="510880", name="红利ETF", market="SH", category="红利"))
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSessionLocal
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /pools (list)
# ---------------------------------------------------------------------------


def test_list_pools_empty(client):
    c, _ = client
    res = c.get("/api/v1/pools")
    assert res.status_code == 200
    assert res.json() == {"items": [], "total": 0}


def test_list_pools_with_items(client):
    c, _ = client
    c.post("/api/v1/pools", json={
        "name": "宽基核心", "description": "沪深300+中证500",
        "etf_codes": ["510300", "510500"],
    })
    res = c.get("/api/v1/pools")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "宽基核心"
    assert body["items"][0]["member_count"] == 2


# ---------------------------------------------------------------------------
# POST /pools
# ---------------------------------------------------------------------------


def test_create_pool_happy_path(client):
    c, _ = client
    res = c.post("/api/v1/pools", json={
        "name": "宽基核心",
        "description": "沪深300+中证500",
        "etf_codes": ["510300", "510500"],
    })
    assert res.status_code == 201
    body = res.json()
    assert body["id"] > 0
    assert body["name"] == "宽基核心"
    assert body["description"] == "沪深300+中证500"
    assert len(body["members"]) == 2
    codes = [m["code"] for m in body["members"]]
    assert codes == ["510300", "510500"]
    # members 应该带 ETF 字典信息
    assert body["members"][0]["name"] == "沪深300ETF"
    assert body["members"][0]["market"] == "SH"


def test_create_pool_duplicate_name_returns_409(client):
    c, _ = client
    body = {"name": "宽基核心", "etf_codes": ["510300"]}
    assert c.post("/api/v1/pools", json=body).status_code == 201
    res = c.post("/api/v1/pools", json=body)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_create_pool_unknown_etf_code_returns_422(client):
    c, _ = client
    res = c.post("/api/v1/pools", json={
        "name": "测试池",
        "etf_codes": ["510300", "999999"],
    })
    assert res.status_code == 422
    assert "999999" in res.json()["detail"]


def test_create_pool_empty_etf_codes_rejected_by_pydantic(client):
    c, _ = client
    res = c.post("/api/v1/pools", json={"name": "空池", "etf_codes": []})
    # Pydantic Field(min_length=1) → 422
    assert res.status_code == 422


def test_create_pool_missing_name_rejected(client):
    c, _ = client
    res = c.post("/api/v1/pools", json={"etf_codes": ["510300"]})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# GET /pools/{id} (detail)
# ---------------------------------------------------------------------------


def test_get_pool_detail(client):
    c, _ = client
    create = c.post("/api/v1/pools", json={
        "name": "宽基核心",
        "description": "d",
        "etf_codes": ["510300", "510500"],
    })
    pid = create.json()["id"]
    res = c.get(f"/api/v1/pools/{pid}")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == pid
    assert body["name"] == "宽基核心"
    assert {m["code"] for m in body["members"]} == {"510300", "510500"}


def test_get_pool_not_found_returns_404(client):
    c, _ = client
    res = c.get("/api/v1/pools/9999")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# PUT /pools/{id}
# ---------------------------------------------------------------------------


def test_update_pool_replaces_members(client):
    c, _ = client
    create = c.post("/api/v1/pools", json={
        "name": "宽基核心",
        "etf_codes": ["510300", "510500"],
    })
    pid = create.json()["id"]
    res = c.put(f"/api/v1/pools/{pid}", json={
        "name": "宽基核心",
        "description": "updated",
        "etf_codes": ["510300", "510880"],
    })
    assert res.status_code == 200
    body = res.json()
    assert body["description"] == "updated"
    assert {m["code"] for m in body["members"]} == {"510300", "510880"}


def test_update_pool_rename_to_taken_returns_409(client):
    c, _ = client
    c.post("/api/v1/pools", json={"name": "池A", "etf_codes": ["510300"]})
    pid_b = c.post("/api/v1/pools", json={
        "name": "池B", "etf_codes": ["510500"],
    }).json()["id"]
    res = c.put(f"/api/v1/pools/{pid_b}", json={
        "name": "池A", "etf_codes": ["510500"],
    })
    assert res.status_code == 409


def test_update_pool_unknown_etf_code_returns_422(client):
    c, _ = client
    pid = c.post("/api/v1/pools", json={
        "name": "测试池", "etf_codes": ["510300"],
    }).json()["id"]
    res = c.put(f"/api/v1/pools/{pid}", json={
        "name": "测试池", "etf_codes": ["510300", "999999"],
    })
    assert res.status_code == 422


def test_update_pool_not_found_returns_404(client):
    c, _ = client
    res = c.put("/api/v1/pools/9999", json={
        "name": "x", "etf_codes": ["510300"],
    })
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /pools/{id}
# ---------------------------------------------------------------------------


def test_delete_pool_returns_204(client):
    c, _ = client
    pid = c.post("/api/v1/pools", json={
        "name": "测试池", "etf_codes": ["510300"],
    }).json()["id"]
    res = c.delete(f"/api/v1/pools/{pid}")
    assert res.status_code == 204
    # 列表为空
    assert c.get("/api/v1/pools").json()["total"] == 0


def test_delete_pool_is_idempotent(client):
    c, _ = client
    res = c.delete("/api/v1/pools/9999")
    assert res.status_code == 204

"""get_db 依赖的测试。"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.models.etf import ETF


@pytest.fixture()
def client_with_db():
    """替换 engine 为内存 SQLite，构造一个最小 FastAPI app。"""
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

    app = FastAPI()

    @app.get("/count")
    def count(db=Depends(get_db)):
        return db.query(ETF).count()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestSessionLocal


def test_get_db_yields_session(client_with_db):
    client, _ = client_with_db
    response = client.get("/count")
    assert response.status_code == 200
    assert response.json() == 0


def test_get_db_rollback_on_exception():
    """当依赖调用方抛出异常时，get_db 内部应执行 rollback 并 re-raise。"""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    import app.db.session as session_mod
    session_mod.SessionLocal = TestSessionLocal

    db_gen = get_db()
    db = next(db_gen)
    # 写入一条未提交的记录
    db.add(ETF(code="510300", name="沪深300ETF", market="SH"))

    # 使用 throw() 把异常注入到 generator 的 yield 处，触发 except 分支
    with pytest.raises(RuntimeError, match="simulated"):
        db_gen.throw(RuntimeError, RuntimeError("simulated"))

    # 异常路径下应该回滚：开启新 session 不应看到未提交的数据
    with TestSessionLocal() as verify_db:
        assert verify_db.query(ETF).count() == 0

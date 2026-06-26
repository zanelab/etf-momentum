"""pytest 公共 fixture：内存 SQLite + 每测试独立 Session。"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import BacktestRun, DailyPrice, ETF, SignalSnapshot  # noqa: F401 触发 metadata 注册


@pytest.fixture()
def engine():
    """每个测试一个全新的内存 SQLite engine。"""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """提供 Session 实例，结束自动 close。"""
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

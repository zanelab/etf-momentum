"""数据库 engine / SessionLocal / get_db（FastAPI Depends）。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL

# SQLite 需要 check_same_thread=False 才能在多线程/请求场景下复用连接
_engine_kwargs: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends 入口：yield session，异常时 rollback，结束关闭。"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

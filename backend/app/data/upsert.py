"""SQLite upsert 工具（基于 SQLAlchemy dialect-specific insert）。"""

from sqlalchemy import insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.data.client import DailyPriceRow, EtfMasterRow
from app.models.daily_price import DailyPrice
from app.models.etf import ETF


def upsert_etf(session: Session, row: EtfMasterRow) -> None:
    """按 code 唯一索引 upsert ETF 主数据。"""
    stmt = sqlite_insert(ETF).values(
        code=row.code,
        name=row.name,
        market=row.market,
        category=row.category,
    ).on_conflict_do_update(
        index_elements=[ETF.code],
        set_={
            "name": row.name,
            "market": row.market,
            "category": row.category,
        },
    )
    session.execute(stmt)


def upsert_daily_price(session: Session, code: str, row: DailyPriceRow) -> None:
    """按 (code, date) 复合唯一索引 upsert 日线行情。"""
    stmt = sqlite_insert(DailyPrice).values(
        code=code,
        date=row.date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
    ).on_conflict_do_update(
        index_elements=[DailyPrice.code, DailyPrice.date],
        set_={
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
        },
    )
    session.execute(stmt)


__all__ = ["upsert_etf", "upsert_daily_price", "insert"]

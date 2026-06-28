"""Per-(code, trade_date) OHLCV cache row for the real-time data source."""
from datetime import date as date_cls
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class MarketBarCache(SQLModel, table=True):
    """Cached market bar; composite primary key (code, trade_date)."""

    __tablename__ = "market_bar_cache"

    code: str = Field(primary_key=True, max_length=32)
    trade_date: date_cls = Field(primary_key=True)
    open: float
    high: float
    low: float
    close: float
    volume: float
    money: Optional[float] = Field(default=None)
    cached_at: datetime
    source: str = Field(default="akshare", max_length=32)

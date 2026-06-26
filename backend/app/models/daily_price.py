"""日线行情实体。"""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint("code", "date", name="uq_daily_prices_code_date"),
        Index("ix_daily_prices_code", "code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    def __repr__(self) -> str:
        return f"<DailyPrice code={self.code} date={self.date} close={self.close}>"

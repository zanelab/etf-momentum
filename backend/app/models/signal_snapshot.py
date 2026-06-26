"""信号快照实体。"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SignalSnapshot(Base):
    __tablename__ = "signal_snapshots"
    __table_args__ = (
        UniqueConstraint("date", "etf_code", name="uq_signal_snapshots_date_etf"),
        Index("ix_signal_snapshots_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    etf_code: Mapped[str] = mapped_column(String(10), nullable=False)
    momentum_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SignalSnapshot date={self.date} etf={self.etf_code} rank={self.rank}>"

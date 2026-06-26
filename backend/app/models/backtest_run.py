"""回测运行记录实体。"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    etf_pool: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    momentum_window: Mapped[int] = mapped_column(Integer, nullable=False)
    rebalance_freq: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<BacktestRun id={self.id} window={self.momentum_window}>"

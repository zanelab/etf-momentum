"""ETF 实体。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ETF(Base):
    __tablename__ = "etfs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ETF code={self.code} name={self.name}>"

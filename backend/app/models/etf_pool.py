"""ETF 策略池实体。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass


class EtfPool(Base):
    """用户自建的策略池。"""

    __tablename__ = "etf_pools"
    __table_args__ = (
        UniqueConstraint("name", name="uq_etf_pools_name"),
        Index("ix_etf_pools_name", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    members: Mapped[list["EtfPoolMember"]] = relationship(
        "EtfPoolMember",
        back_populates="pool",
        cascade="all, delete-orphan",
        order_by="EtfPoolMember.position",
    )

    def __repr__(self) -> str:
        return f"<EtfPool id={self.id} name={self.name!r}>"


class EtfPoolMember(Base):
    """池与 ETF 的多对多成员关系。"""

    __tablename__ = "etf_pool_members"

    pool_id: Mapped[int] = mapped_column(
        ForeignKey("etf_pools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    etf_code: Mapped[str] = mapped_column(
        ForeignKey("etfs.code"), primary_key=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    pool: Mapped[EtfPool] = relationship("EtfPool", back_populates="members")

    def __repr__(self) -> str:
        return f"<EtfPoolMember pool_id={self.pool_id} code={self.etf_code}>"

from typing import Optional, List

"""Static ETF pool entry."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class StaticPool(SQLModel, table=True):
    """Static ETF pool entry."""

    __tablename__ = "static_pool"

    code: str = Field(primary_key=True, max_length=32)
    display_name: Optional[str] = Field(default=None, max_length=128)
    enabled: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

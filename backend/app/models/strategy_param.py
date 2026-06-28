"""Strategy parameter (single key, JSON-encoded value)."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class StrategyParam(SQLModel, table=True):
    """Strategy parameter (single key, JSON-encoded value)."""

    __tablename__ = "strategy_param"

    key: str = Field(primary_key=True, max_length=64)
    value_json: str = Field(nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

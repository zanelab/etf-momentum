"""Portfolio model: user-held ETF positions."""
from datetime import datetime

from sqlmodel import Field, SQLModel


class Portfolio(SQLModel, table=True):
    """One row per ETF position held by the user."""

    __tablename__ = "portfolio"

    code: str = Field(primary_key=True, max_length=32)
    name: str = Field(max_length=128)
    shares: int = Field(nullable=False)
    cost_price: float = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
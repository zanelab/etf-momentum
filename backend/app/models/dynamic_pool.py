"""Dynamic ETF pool entry: full-market ETF list from akshare."""
from datetime import datetime

from sqlmodel import Field, SQLModel


class DynamicPoolEntry(SQLModel, table=True):
    """One row per ETF in the full-market pool synced from akshare.

    Users opt in by setting `is_enabled=True`; filter_etfs reads only
    enabled rows as the dynamic pool.
    """

    __tablename__ = "dynamic_pool_entry"

    code: str = Field(primary_key=True, max_length=32)
    name: str = Field(max_length=128)
    is_enabled: bool = Field(default=False, nullable=False)
    last_synced_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

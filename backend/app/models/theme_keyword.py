from typing import Optional, List
"""Theme keyword dictionary entry."""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class ThemeKeyword(SQLModel, table=True):
    """Theme keyword dictionary entry."""

    __tablename__ = "theme_keyword"

    id: Optional[int] = Field(default=None, primary_key=True)
    theme: str = Field(index=True, max_length=64, nullable=False)
    keyword: str = Field(max_length=64, nullable=False, unique=True)

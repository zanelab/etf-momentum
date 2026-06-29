"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StaticPoolEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(min_length=4, max_length=32)
    display_name: str | None = None
    enabled: bool = True


class StaticPoolReplace(BaseModel):
    """Replace the entire static pool atomically."""

    entries: list[StaticPoolEntry]


class StaticPoolUpdate(BaseModel):
    """Partial update of a single entry."""

    enabled: bool | None = None
    display_name: str | None = None


class ThemeDictionary(BaseModel):
    """Full theme dictionary as { theme: [keywords] }."""

    themes: dict[str, list[str]]


class StrategyParams(BaseModel):
    """Strategy parameters; arbitrary JSON-compatible dict.

    PUT semantics: merge with existing values (do not replace keys not present).
    """

    params: dict[str, Any]


class DynamicPoolEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    is_enabled: bool
    last_synced_at: datetime


class DynamicPoolSyncResult(BaseModel):
    synced: int
    total: int
    enabled: int


class DynamicPoolUpdate(BaseModel):
    is_enabled: bool | None = None


class SyncETFStatus(BaseModel):
    """Per-ETF historical-sync state surfaced by the sync API."""

    code: str
    name: str | None
    last_synced_date: str | None
    status: Literal["ok", "failed", "missing", "never"]
    error: str | None = None


class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]


class SyncTriggerResult(SyncStatusResponse):
    """Result of a manual historical-sync trigger."""

    synced_count: int
    run_at: datetime

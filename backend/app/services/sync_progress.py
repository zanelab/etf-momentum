"""Process-singleton in-memory tracker for in-progress historical sync.

This is a module-level singleton; tests should construct a fresh
`SyncProgressTracker()` rather than relying on the singleton.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ProgressInfo(BaseModel):
    code: str
    from_date: date
    to_date: date
    current_date: date
    total_days: int
    completed_days: int
    overall_index: int
    overall_total: int
    started_at: datetime


class SyncProgressTracker:
    """dict[code, ProgressInfo] backed by a private dict."""

    def __init__(self) -> None:
        self._by_code: dict[str, ProgressInfo] = {}
        self._cancel_requested: bool = False

    def set(self, code: str, info: ProgressInfo) -> None:
        self._by_code[code] = info

    def get_all(self) -> list[ProgressInfo]:
        return list(self._by_code.values())

    def clear(self) -> None:
        self._by_code.clear()
        self._cancel_requested = False

    def is_active(self) -> bool:
        return bool(self._by_code)

    def cancel(self) -> None:
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def reset_cancel(self) -> None:
        self._cancel_requested = False


# module-level singleton used by sync service + status endpoint
tracker = SyncProgressTracker()

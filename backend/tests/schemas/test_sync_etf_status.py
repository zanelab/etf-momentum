"""Tests for extended SyncETFStatus schema."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import ProgressSnapshot, SyncETFStatus


def test_sync_etf_status_minimal_fields():
    """Existing minimal shape still works (backward compat)."""
    s = SyncETFStatus(code="510300.XSHG", name="沪深300ETF", last_synced_date=None,
                      status="never", error=None)
    assert s.code == "510300.XSHG"
    assert s.is_enabled is True
    assert s.last_synced_at is None
    assert s.progress is None


def test_sync_etf_status_with_dynamic_fields():
    """is_enabled + last_synced_at fields populate from dynamic_pool_entry."""
    now = datetime.now(timezone.utc)
    s = SyncETFStatus(
        code="510500.XSHG", name="中证500ETF", last_synced_date="2024-04-21",
        last_synced_at=now, is_enabled=False, status="ok", error=None,
    )
    assert s.is_enabled is False
    assert s.last_synced_at == now


def test_sync_etf_status_in_progress_carries_progress():
    """status='in_progress' requires progress field; omitempty when not."""
    snap = ProgressSnapshot(completed=5, total=10, current_code="510300.XSHG",
                            current_date=date(2024, 4, 21), percent=50)
    s = SyncETFStatus(code="510300.XSHG", name=None, last_synced_date=None,
                      status="in_progress", error=None, progress=snap)
    assert s.status == "in_progress"
    assert s.progress is not None
    assert s.progress.percent == 50


def test_progress_snapshot_rejects_invalid_percent_types():
    """ProgressSnapshot percent is int."""
    with pytest.raises(ValidationError):
        ProgressSnapshot(completed="abc", total=10, current_code="x",
                         current_date=date(2024, 4, 21), percent=50)


def test_sync_etf_status_accepts_in_progress_literal():
    """status Literal expanded to include 'in_progress'."""
    s = SyncETFStatus(code="x", name=None, last_synced_date=None,
                      status="in_progress", error=None)
    assert s.status == "in_progress"

from datetime import date, datetime, timezone

from app.services.sync_progress import ProgressInfo, SyncProgressTracker, tracker


def test_tracker_starts_inactive():
    t = SyncProgressTracker()
    assert t.is_active() is False
    assert t.get_all() == []

def test_tracker_set_marks_active():
    t = SyncProgressTracker()
    info = ProgressInfo(
        code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
        current_date=date(2024,1,1), total_days=31, completed_days=1,
        overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc),
    )
    t.set("510300", info)
    assert t.is_active() is True
    assert t.get_all() == [info]

def test_tracker_overwrite_same_code():
    t = SyncProgressTracker()
    info1 = ProgressInfo(code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
                         current_date=date(2024,1,1), total_days=31, completed_days=1,
                         overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc))
    info2 = info1.model_copy(update={"current_date": date(2024,1,2), "completed_days": 2, "overall_index": 2})
    t.set("510300", info1)
    t.set("510300", info2)
    assert len(t.get_all()) == 1
    assert t.get_all()[0].current_date == date(2024,1,2)

def test_tracker_clear_resets():
    t = SyncProgressTracker()
    info = ProgressInfo(code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
                        current_date=date(2024,1,1), total_days=31, completed_days=1,
                        overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc))
    t.set("510300", info)
    t.clear()
    assert t.is_active() is False
    assert t.get_all() == []

def test_module_singleton_exists():
    assert isinstance(tracker, SyncProgressTracker)

def test_tracker_cancel_starts_false():
    t = SyncProgressTracker()
    assert t.is_cancel_requested() is False

def test_tracker_cancel_sets_flag():
    t = SyncProgressTracker()
    t.cancel()
    assert t.is_cancel_requested() is True

def test_tracker_reset_cancel_clears_flag():
    t = SyncProgressTracker()
    t.cancel()
    t.reset_cancel()
    assert t.is_cancel_requested() is False

def test_tracker_clear_also_resets_cancel():
    """clear() 是 sync 完成时的清理点，应同时清除 cancel flag。"""
    t = SyncProgressTracker()
    info = ProgressInfo(code="510300", from_date=date(2024,1,1), to_date=date(2024,1,31),
                        current_date=date(2024,1,1), total_days=31, completed_days=1,
                        overall_index=1, overall_total=31, started_at=datetime.now(timezone.utc))
    t.set("510300", info)
    t.cancel()
    t.clear()
    assert t.is_cancel_requested() is False
    assert t.is_active() is False

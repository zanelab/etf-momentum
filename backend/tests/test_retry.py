"""Tests for retry_with_backoff helper."""

import pytest

from app.data_sources.retry import retry_with_backoff


class _FlakyError(RuntimeError):
    """Marker error for retry tests."""


def test_retry_returns_value_on_first_success() -> None:
    calls = []

    def fn() -> int:
        calls.append(1)
        return 42

    result = retry_with_backoff(fn, max_retries=3, backoff_factor=2.0, initial_delay=0.0)
    assert result == 42
    assert len(calls) == 1


def test_retry_recovers_on_second_attempt() -> None:
    calls = []

    def fn() -> int:
        calls.append(1)
        if len(calls) < 2:
            raise _FlakyError("transient")
        return 7

    result = retry_with_backoff(fn, max_retries=3, backoff_factor=2.0, initial_delay=0.0)
    assert result == 7
    assert len(calls) == 2


def test_retry_exhausts_all_attempts_then_raises() -> None:
    calls = []

    def fn() -> int:
        calls.append(1)
        raise _FlakyError(f"attempt {len(calls)}")

    with pytest.raises(_FlakyError, match="attempt 4"):
        retry_with_backoff(fn, max_retries=3, backoff_factor=2.0, initial_delay=0.0)
    assert len(calls) == 4  # 1 initial + 3 retries


def test_retry_does_not_retry_on_max_retries_zero() -> None:
    calls = []

    def fn() -> int:
        calls.append(1)
        raise _FlakyError("nope")

    with pytest.raises(_FlakyError):
        retry_with_backoff(fn, max_retries=0, backoff_factor=2.0, initial_delay=0.0)
    assert len(calls) == 1


def test_retry_sleeps_between_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the backoff schedule: sleeps with [initial, initial*f, initial*f^2, ...]."""
    sleeps: list[float] = []
    monkeypatch.setattr("app.data_sources.retry.time.sleep", lambda s: sleeps.append(s))

    def fn() -> int:
        if len(sleeps) < 3:
            raise _FlakyError("again")
        return 1

    retry_with_backoff(fn, max_retries=3, backoff_factor=2.0, initial_delay=1.0)
    # After attempt 0 fails -> sleep 1.0; after attempt 1 fails -> sleep 2.0;
    # after attempt 2 fails -> sleep 4.0; attempt 3 succeeds.
    assert sleeps == [1.0, 2.0, 4.0]


def test_retry_propagates_non_retryable_when_typed() -> None:
    """If the function raises a non-retryable type (e.g., ValueError) we still retry
    unless the caller filters. The default behavior retries all exceptions.
    """
    calls = []

    def fn() -> int:
        calls.append(1)
        raise ValueError("bad arg")

    with pytest.raises(ValueError):
        retry_with_backoff(fn, max_retries=2, backoff_factor=2.0, initial_delay=0.0)
    assert len(calls) == 3  # default: retry on any exception

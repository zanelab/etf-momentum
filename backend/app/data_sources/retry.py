"""Retry helper with exponential backoff for transient data-source failures."""
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
) -> T:
    """Call `fn` with exponential backoff on exception.

    - Attempts the call up to ``max_retries + 1`` times total.
    - On exception, sleeps ``initial_delay * backoff_factor ** attempt`` seconds
      before the next attempt, where ``attempt`` is the 0-indexed failure count.
    - Re-raises the last exception if all attempts fail.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt == max_retries:
                break
            sleep_for = initial_delay * (backoff_factor ** attempt)
            time.sleep(sleep_for)
    assert last_err is not None
    raise last_err

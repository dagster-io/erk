"""Retry utility for GitHub API calls with exponential backoff."""

import sys
from collections.abc import Callable
from typing import TypeVar

from erk_shared.gateway.time.abc import Time

# Retry delays following exponential backoff pattern: [0.5, 1.0] (~1.5s max, 2 retries)
RETRY_DELAYS = [0.5, 1.0]

T = TypeVar("T")


def with_github_retry(
    time: Time,
    operation_name: str,
    fn: Callable[[], T],
) -> T:
    """Execute function with GitHub API retry logic.

    Retries RuntimeError exceptions with exponential backoff. This handles
    transient GitHub API failures (network errors, rate limits, etc.) while
    allowing permanent failures to surface after exhausting retries.

    Args:
        time: Time abstraction for sleep operations (enables fast tests)
        operation_name: Description of operation for logging
        fn: Function to execute with retries (should be a lambda or callable)

    Returns:
        Result from successful function call

    Raises:
        RuntimeError: If all retry attempts fail

    Example:
        result = with_github_retry(
            self._time,
            "fetch comment",
            lambda: self._api.get_comment_by_id(comment_id)
        )
    """
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            result = fn()
            if attempt > 0:
                print(
                    f"Successfully completed {operation_name} on retry {attempt}",
                    file=sys.stderr,
                )
            return result
        except RuntimeError as e:
            is_last_attempt = attempt == len(RETRY_DELAYS)
            if is_last_attempt:
                print(
                    f"Failed {operation_name} after {len(RETRY_DELAYS) + 1} attempts: {e}",
                    file=sys.stderr,
                )
                raise

            delay = RETRY_DELAYS[attempt]
            print(
                f"Failed {operation_name} (attempt {attempt + 1}): {e}",
                file=sys.stderr,
            )
            print(f"Retrying in {delay}s...", file=sys.stderr)
            time.sleep(delay)

    # This should never be reached due to raise in last attempt
    raise AssertionError("Retry logic error: should have raised in last attempt")

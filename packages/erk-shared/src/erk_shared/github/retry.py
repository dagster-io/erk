"""GitHub API retry utilities with configurable delays and exception handling."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TypeVar

from erk_shared.gateway.time.abc import Time

# Default retry delays for transient error retry (exponential backoff)
RETRY_DELAYS = [0.5, 1.0]

T = TypeVar("T")


class ShouldRetry(Exception):
    """Raised by callback to signal that operation should be retried.

    This exception is used for control flow in retry logic. The callback
    function raises this when it encounters a transient error or when
    polling for eventual consistency and the desired state hasn't been
    reached yet.
    """


def with_github_retry(
    time: Time,
    operation_name: str,
    fn: Callable[[], T],
    retry_delays: list[float] | None = None,
) -> T:
    """Execute function with configurable retry logic.

    Supports both transient error retry (quick exponential backoff) and
    eventual consistency polling (longer constant intervals).

    The callback controls retry behavior by raising ShouldRetry exception.
    Any other exception bubbles up immediately (permanent failure).

    Args:
        time: Time abstraction for sleep operations
        operation_name: Description for logging
        fn: Function to execute with retries. Should raise ShouldRetry to retry,
           or return success value, or raise other exception for permanent failure.
        retry_delays: Custom delays. Defaults to [0.5, 1.0] for transient errors.
                     Use [2.0] * 15 for polling (30s total).

    Returns:
        Result from successful function call

    Raises:
        ShouldRetry: If all retry attempts exhausted
        Any other exception: Permanent failure from callback

    Examples:
        # Transient error retry (callback handles RuntimeError):
        def fetch_with_retry():
            try:
                return self._api.get_comment_by_id(id)
            except RuntimeError as e:
                # Transient error - retry
                raise ShouldRetry(f"API error: {e}") from e

        comment = with_github_retry(self._time, "fetch comment", fetch_with_retry)

        # Polling for eventual consistency (callback raises ShouldRetry when not ready):
        def poll_for_run():
            try:
                runs = self._fetch_runs()
                run = self._find_matching_run(runs, branch)
                if run:
                    return run
                # Not found yet - keep polling
                raise ShouldRetry("Run not found yet")
            except (RuntimeError, FileNotFoundError) as e:
                # Transient API error - retry
                raise ShouldRetry(f"API error: {e}") from e

        run = with_github_retry(
            self._time,
            "poll for workflow run",
            poll_for_run,
            retry_delays=[2.0] * 15  # 30s total
        )
    """
    delays = retry_delays if retry_delays is not None else RETRY_DELAYS

    for attempt in range(len(delays) + 1):
        try:
            result = fn()
            if attempt > 0:
                print(f"Success on retry {attempt}: {operation_name}", file=sys.stderr)
            return result
        except ShouldRetry as e:
            is_last_attempt = attempt == len(delays)
            if is_last_attempt:
                print(
                    f"Failed after {len(delays) + 1} attempts: {operation_name}: {e}",
                    file=sys.stderr,
                )
                raise

            delay = delays[attempt]
            print(
                f"Retry {attempt + 1} after {delay}s: {operation_name}: {e}",
                file=sys.stderr,
            )
            time.sleep(delay)

    msg = "Retry logic error"
    raise AssertionError(msg)

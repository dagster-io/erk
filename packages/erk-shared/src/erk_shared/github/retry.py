"""Retry utilities with configurable delays and return-value control flow."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from erk_shared.gateway.time.abc import Time

# Default retry delays for transient error retry (exponential backoff)
RETRY_DELAYS = [0.5, 1.0]

T = TypeVar("T")


@dataclass(frozen=True)
class RetryRequested:
    """Callback returns this to signal that retry is needed.

    Used by callbacks to indicate a transient error or that the desired
    state hasn't been reached yet (eventual consistency polling).

    Attributes:
        reason: Human-readable description of why retry is needed
    """

    reason: str


@dataclass(frozen=True)
class RetriesExhausted:
    """Returned by with_retries when all retry attempts failed.

    Distinct from RetryRequested to clarify semantics:
    - RetryRequested: callback signals "try again"
    - RetriesExhausted: with_retries signals "gave up after N attempts"

    Attributes:
        reason: The reason from the last RetryRequested
    """

    reason: str


def with_retries(
    time: Time,
    operation_name: str,
    fn: Callable[[], T | RetryRequested],
    retry_delays: list[float] | None = None,
) -> T | RetriesExhausted:
    """Execute function with configurable retry logic.

    Supports both transient error retry (quick exponential backoff) and
    eventual consistency polling (longer constant intervals).

    The callback controls retry behavior by returning RetryRequested sentinel.
    Any exception from callback bubbles up immediately (permanent failure).

    Args:
        time: Time abstraction for sleep operations
        operation_name: Description for logging
        fn: Function to execute with retries. Should return RetryRequested to retry,
           or return success value. Exceptions indicate permanent failure.
        retry_delays: Custom delays. Defaults to [0.5, 1.0] for transient errors.
                     Use [2.0] * 15 for polling (30s total).

    Returns:
        Success value from callback, or RetriesExhausted if all attempts failed

    Examples:
        # Transient error retry (callback catches and converts to RetryRequested):
        def fetch_with_retry():
            try:
                return self._api.get_comment_by_id(id)
            except RuntimeError as e:
                # Transient error - retry
                return RetryRequested(reason=f"API error: {e}")
            # Let other exceptions bubble up as permanent failures

        result = with_retries(self._time, "fetch comment", fetch_with_retry)
        if isinstance(result, RetriesExhausted):
            handle_failure(result.reason)
        else:
            use_comment(result)

        # Polling for eventual consistency:
        def poll_for_run():
            try:
                runs = self._fetch_runs()
            except (RuntimeError, FileNotFoundError) as e:
                # Transient API error - retry
                return RetryRequested(reason=f"API error: {e}")

            run = self._find_matching_run(runs, branch)
            if run:
                return run
            # Not found yet - keep polling
            return RetryRequested(reason="Run not found yet")

        result = with_retries(
            self._time,
            "poll for workflow run",
            poll_for_run,
            retry_delays=[2.0] * 15  # 30s total
        )
        if isinstance(result, RetriesExhausted):
            return None  # Timeout
        return result
    """
    delays = retry_delays if retry_delays is not None else RETRY_DELAYS

    for attempt in range(len(delays) + 1):
        result = fn()

        if not isinstance(result, RetryRequested):
            if attempt > 0:
                print(f"Success on retry {attempt}: {operation_name}", file=sys.stderr)
            return result

        # Result is RetryRequested - check if we have more attempts
        is_last_attempt = attempt == len(delays)
        if is_last_attempt:
            print(
                f"Failed after {len(delays) + 1} attempts: {operation_name}: {result.reason}",
                file=sys.stderr,
            )
            return RetriesExhausted(reason=result.reason)

        delay = delays[attempt]
        print(
            f"Retry {attempt + 1} after {delay}s: {operation_name}: {result.reason}",
            file=sys.stderr,
        )
        time.sleep(delay)

    msg = "Retry logic error"
    raise AssertionError(msg)

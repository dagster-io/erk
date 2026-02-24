"""Fake Time implementation for testing.

FakeTime is an in-memory implementation that tracks sleep() calls without
actually sleeping, returns a configurable current time, and provides
deterministic monotonic clock values from a configured sequence.
"""

from collections.abc import Sequence
from datetime import datetime

from erk_shared.gateway.time.abc import Time

# Default fixed time for deterministic tests: 2024-01-15 14:30:00
DEFAULT_FAKE_TIME = datetime(2024, 1, 15, 14, 30, 0)


class FakeTime(Time):
    """In-memory fake implementation that tracks calls without sleeping.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(
        self,
        current_time: datetime | None = None,
        monotonic_values: Sequence[float] | None = None,
    ) -> None:
        """Create FakeTime with empty call tracking and optional fixed time.

        Args:
            current_time: Fixed datetime to return from now(). Defaults to
                2024-01-15 14:30:00 for deterministic tests.
            monotonic_values: Sequence of floats to return from monotonic().
                Returns values in order; repeats last value when exhausted.
                Defaults to [0.0].
        """
        self._sleep_calls: list[float] = []
        self._current_time = current_time if current_time is not None else DEFAULT_FAKE_TIME
        self._monotonic_values: Sequence[float] = (
            monotonic_values if monotonic_values is not None else [0.0]
        )
        self._monotonic_index: int = 0

    @property
    def sleep_calls(self) -> list[float]:
        """Get the list of sleep() calls that were made.

        Returns list of seconds values passed to sleep().

        This property is for test assertions only.
        """
        return self._sleep_calls

    def sleep(self, seconds: float) -> None:
        """Track sleep call without actually sleeping.

        Args:
            seconds: Number of seconds that would have been slept
        """
        self._sleep_calls.append(seconds)

    def now(self) -> datetime:
        """Get the configured current datetime.

        Returns:
            The fixed datetime configured at construction time.
        """
        return self._current_time

    def monotonic(self) -> float:
        """Get the next monotonic value from the configured sequence.

        Returns values from the monotonic_values sequence in order.
        When the sequence is exhausted, repeats the last value.

        Returns:
            The next float from the configured sequence.
        """
        idx = self._monotonic_index if self._monotonic_index < len(self._monotonic_values) else -1
        self._monotonic_index += 1
        return self._monotonic_values[idx]

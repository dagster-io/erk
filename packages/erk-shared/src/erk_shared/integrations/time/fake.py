"""Fake Time implementation for testing.

FakeTime is an in-memory implementation that tracks sleep() calls without
actually sleeping and returns a configurable current time, enabling fast
and deterministic tests.
"""

from datetime import datetime

from erk_shared.integrations.time.abc import Time

# Default fixed time for deterministic tests: 2024-01-15 14:30:00
DEFAULT_FAKE_TIME = datetime(2024, 1, 15, 14, 30, 0)


class FakeTime(Time):
    """In-memory fake implementation that tracks calls without sleeping.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(self, current_time: datetime | None = None) -> None:
        """Create FakeTime with empty call tracking and optional fixed time.

        Args:
            current_time: Fixed datetime to return from now(). Defaults to
                2024-01-15 14:30:00 for deterministic tests.
        """
        self._sleep_calls: list[float] = []
        self._current_time = current_time if current_time is not None else DEFAULT_FAKE_TIME

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

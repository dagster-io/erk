"""Time operations abstraction for testing.

This module provides an ABC for time operations (sleep, now) to enable
fast tests that don't actually sleep and can use deterministic timestamps.
"""

from abc import ABC, abstractmethod
from datetime import datetime


class Time(ABC):
    """Abstract time operations for dependency injection."""

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Sleep for specified number of seconds.

        Args:
            seconds: Number of seconds to sleep
        """
        ...

    @abstractmethod
    def now(self) -> datetime:
        """Get the current datetime.

        Returns:
            Current datetime (timezone-naive for simplicity)
        """
        ...

    @abstractmethod
    def monotonic(self) -> float:
        """Get a monotonic clock value for measuring elapsed time.

        Returns:
            A float representing seconds from an arbitrary reference point.
            Only differences between calls are meaningful.
        """
        ...

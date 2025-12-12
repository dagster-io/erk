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

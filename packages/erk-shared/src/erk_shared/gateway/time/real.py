"""Real time implementation using actual time.sleep() and datetime.now()."""

import time
from datetime import datetime

from erk_shared.gateway.time.abc import Time


class RealTime(Time):
    """Production implementation using actual time.sleep() and datetime.now()."""

    def sleep(self, seconds: float) -> None:
        """Sleep for specified number of seconds using time.sleep().

        Args:
            seconds: Number of seconds to sleep
        """
        time.sleep(seconds)

    def now(self) -> datetime:
        """Get the current datetime using datetime.now().

        Returns:
            Current datetime (timezone-naive)
        """
        return datetime.now()

    def monotonic(self) -> float:
        """Get the current monotonic clock value using time.monotonic().

        Returns:
            Monotonic clock value in fractional seconds
        """
        return time.monotonic()

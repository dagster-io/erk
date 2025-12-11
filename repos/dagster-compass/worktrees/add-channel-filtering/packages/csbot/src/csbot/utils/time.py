"""Time provider abstraction for testable time-dependent operations.

This module provides dependency injection for time operations, enabling deterministic
testing of time-dependent code.

Core Concepts:
    Type Aliases:
        - DatetimeNow: Callable that returns current datetime
        - SecondsNow: Callable that returns current time as seconds since epoch
        - AsyncSleep: Async callable that delays execution for specified duration

    Production Implementations:
        - system_datetime_now(): Returns actual system datetime
        - system_seconds_now(): Returns actual system time in seconds
        - system_async_sleep(): Actual async sleep operation

    Test Implementations:
        - DatetimeNowFake: Controllable datetime provider for testing
        - SecondsNowFake: Controllable seconds provider for testing
        - FakeTimeProvider: Bundled time provider with coordinated time state

Usage Pattern:
    Production Code:
        from csbot.utils.time import DatetimeNow, AsyncSleep
        from csbot.utils.time import system_datetime_now, system_async_sleep

        class MyService:
            def __init__(
                self,
                datetime_now: DatetimeNow = system_datetime_now,
                async_sleep: AsyncSleep = system_async_sleep,
            ):
                self.datetime_now = datetime_now
                self.async_sleep = async_sleep

            async def periodic_task(self):
                while self.running:
                    await self.do_work()
                    await self.async_sleep(5.0)

    Test Code:
        from csbot.utils.time import FakeTimeProvider

        async def test_periodic_task():
            fake_time = FakeTimeProvider(initial_seconds=1000000)
            service = MyService(
                datetime_now=fake_time.datetime_now,
                async_sleep=fake_time.async_sleep,
            )

            await service.start()
            fake_time.advance(15)  # Instantly advance 15 seconds
            assert service.execution_count >= 3

Test Helper Methods:
    DatetimeNowFake / SecondsNowFake:
        - advance_time(seconds): Move time forward by specified seconds
        - set_time(time_seconds): Set to specific timestamp

Common Use Cases:
    - Idle Detection: Track activity and determine idle state based on elapsed time
    - Token Expiry: Check if authentication tokens have expired
    - Scheduling: Test cron job execution at specific times
    - Rate Limiting: Test time-based rate limiting logic
    - Cache Expiry: Validate cache invalidation timing

Best Practices:
    - Always accept time provider as constructor parameter with production default
    - Use type aliases (DatetimeNow, SecondsNow) for clean interfaces
    - In tests, create time provider as fixture for reuse across test methods
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

# Type aliases for clean production interfaces
DatetimeNow = Callable[[], datetime]
SecondsNow = Callable[[], int]
AsyncSleep = Callable[[float], Awaitable[None]]


# Production implementations
def system_datetime_now() -> datetime:
    """Get current system datetime."""
    return datetime.now()


def system_seconds_now() -> int:
    """Get current system time as seconds since epoch."""
    return int(time.time())


async def system_async_sleep(duration: float) -> None:
    """Production async sleep implementation."""
    await asyncio.sleep(duration)


class DatetimeNowFake:
    """Test provider for datetime with controllable time."""

    def __init__(self, initial_time_seconds: int | None = None):
        self._current_time_seconds = initial_time_seconds or int(time.time())

    def __call__(self) -> datetime:
        return datetime.fromtimestamp(self._current_time_seconds)

    def advance_time(self, seconds: int) -> None:
        """Advance the test time by the specified number of seconds."""
        self._current_time_seconds += seconds

    def set_time(self, time_seconds: int) -> None:
        """Set the test time to a specific timestamp."""
        self._current_time_seconds = time_seconds


class SecondsNowFake:
    """Test provider for seconds with controllable time."""

    def __init__(self, initial_time_seconds: int | None = None):
        self._current_time_seconds = initial_time_seconds or int(time.time())

    def __call__(self) -> int:
        return self._current_time_seconds

    def advance_time(self, seconds: int) -> None:
        """Advance the test time by the specified number of seconds."""
        self._current_time_seconds += seconds

    def set_time(self, time_seconds: int) -> None:
        """Set the test time to a specific timestamp."""
        self._current_time_seconds = time_seconds


class FakeTimeProvider:
    """Coordinated fake time provider for deterministic testing.

    Provides datetime_now, seconds_now, and async_sleep with shared time state.
    All providers advance time together, preventing drift.

    Usage:
        fake_time = FakeTimeProvider(initial_seconds=1000000)

        service = MyService(
            datetime_now=fake_time.datetime_now,
            async_sleep=fake_time.async_sleep,
        )

        # Manually advance time
        fake_time.advance(10)

        # async_sleep also advances time
        await fake_time.async_sleep(5.0)  # Advances by 5 seconds
    """

    def __init__(self, initial_seconds: float = 0):
        """Initialize with starting time in seconds since epoch."""
        self.current_seconds = initial_seconds

    def datetime_now(self) -> datetime:
        """Get current fake datetime with UTC timezone."""
        return datetime.fromtimestamp(self.current_seconds, tz=UTC)

    def seconds_now(self) -> int:
        """Get current fake time as seconds since epoch."""
        return int(self.current_seconds)

    async def async_sleep(self, duration: float) -> None:
        """Fake async sleep that instantly advances time instead of waiting.

        Yields control to event loop to prevent infinite loops from blocking.
        """
        self.current_seconds += duration
        await asyncio.sleep(0)  # Yield control to event loop

    async def sleep_and_yield(self, duration: float, yields: int = 20) -> None:
        """Advance time and yield multiple times to let background tasks execute.

        This is a test helper that advances time and yields control repeatedly,
        allowing background tasks to execute multiple cycles.

        Args:
            duration: Seconds to advance fake time
            yields: Number of times to yield to event loop (default 20)
        """
        self.current_seconds += duration
        for _ in range(yields):
            await asyncio.sleep(0)

    def advance(self, seconds: float) -> None:
        """Manually advance fake time by specified seconds."""
        self.current_seconds += seconds

    def set_time(self, seconds: float) -> None:
        """Set fake time to specific timestamp."""
        self.current_seconds = seconds

"""Tests for time provider abstraction."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from csbot.utils.time import (
    AsyncSleep,
    DatetimeNow,
    FakeTimeProvider,
    system_async_sleep,
    system_datetime_now,
    system_seconds_now,
)

if TYPE_CHECKING:
    from csbot.utils.time import (
        SecondsNow,
    )


class TestProductionImplementations:
    """Tests for production time implementations."""

    def test_system_datetime_now_returns_datetime(self):
        """system_datetime_now returns a datetime instance."""
        result = system_datetime_now()
        assert isinstance(result, datetime)

    def test_system_seconds_now_returns_int(self):
        """system_seconds_now returns an integer."""
        result = system_seconds_now()
        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.asyncio
    async def test_system_async_sleep_completes(self):
        """system_async_sleep completes without error."""
        # Use minimal duration to keep test fast
        await system_async_sleep(0.001)


class TestFakeTimeProvider:
    """Tests for FakeTimeProvider coordinated fake time."""

    def test_initial_time(self):
        """FakeTimeProvider initializes with specified time."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        assert fake_time.current_seconds == 1000000
        assert fake_time.seconds_now() == 1000000

    def test_datetime_now_returns_utc(self):
        """datetime_now returns UTC timezone datetime."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        dt = fake_time.datetime_now()
        assert dt.tzinfo == UTC
        assert dt.timestamp() == 1000000

    def test_seconds_now_returns_int(self):
        """seconds_now returns current fake time as int."""
        fake_time = FakeTimeProvider(initial_seconds=1000000.5)
        assert fake_time.seconds_now() == 1000000
        assert fake_time.current_seconds == 1000000.5

    def test_advance_increments_time(self):
        """advance() increments current time."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        fake_time.advance(100)
        assert fake_time.current_seconds == 1000100

    def test_set_time_changes_time(self):
        """set_time() changes current time to specified value."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        fake_time.set_time(2000000)
        assert fake_time.current_seconds == 2000000

    @pytest.mark.asyncio
    async def test_async_sleep_advances_time(self):
        """async_sleep advances time instead of actually sleeping."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)

        await fake_time.async_sleep(10.0)

        # Time advanced by 10 seconds
        assert fake_time.current_seconds == 1000010

    @pytest.mark.asyncio
    async def test_async_sleep_is_instant(self):
        """async_sleep completes instantly without real waiting."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)

        # This would take 100 seconds with real sleep
        await fake_time.async_sleep(100.0)

        # Completes instantly in tests
        assert fake_time.current_seconds == 1000100

    def test_coordinated_time_advancement(self):
        """All time providers see same time advancement."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)

        initial_dt = fake_time.datetime_now()
        initial_seconds = fake_time.seconds_now()

        fake_time.advance(60)

        advanced_dt = fake_time.datetime_now()
        advanced_seconds = fake_time.seconds_now()

        # Both providers advanced by 60 seconds
        assert (advanced_dt - initial_dt).total_seconds() == 60
        assert advanced_seconds - initial_seconds == 60

    @pytest.mark.asyncio
    async def test_async_sleep_coordinates_with_datetime(self):
        """async_sleep advances datetime_now consistently."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)

        dt_before = fake_time.datetime_now()
        await fake_time.async_sleep(30.0)
        dt_after = fake_time.datetime_now()

        # datetime_now reflects async_sleep advancement
        assert (dt_after - dt_before).total_seconds() == 30


class TestTypeAliases:
    """Tests that type aliases work correctly."""

    def test_datetime_now_alias(self):
        """DatetimeNow type alias accepts callable returning datetime."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        provider: DatetimeNow = fake_time.datetime_now

        result = provider()
        assert isinstance(result, datetime)

    def test_seconds_now_alias(self):
        """SecondsNow type alias accepts callable returning number."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        provider: SecondsNow = fake_time.seconds_now

        result = provider()
        assert isinstance(result, (int, float))
        assert result == 1000000

    @pytest.mark.asyncio
    async def test_async_sleep_alias(self):
        """AsyncSleep type alias accepts async callable."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        sleeper: AsyncSleep = fake_time.async_sleep

        await sleeper(5.0)
        assert fake_time.current_seconds == 1000005


class TestDependencyInjectionPattern:
    """Tests demonstrating dependency injection usage."""

    class ServiceWithTime:
        """Example service using time injection."""

        def __init__(
            self,
            datetime_now: DatetimeNow = system_datetime_now,
            async_sleep: AsyncSleep = system_async_sleep,
        ):
            self.datetime_now = datetime_now
            self.async_sleep = async_sleep
            self.execution_count = 0
            self.last_execution: datetime | None = None

        async def execute_periodic_task(self, iterations: int, interval: float):
            """Execute task multiple times with interval between executions."""
            for _ in range(iterations):
                self.execution_count += 1
                self.last_execution = self.datetime_now()
                await self.async_sleep(interval)

    @pytest.mark.asyncio
    async def test_service_uses_fake_time(self):
        """Service with injected fake time completes instantly."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)

        service = self.ServiceWithTime(
            datetime_now=fake_time.datetime_now,
            async_sleep=fake_time.async_sleep,
        )

        # Execute 10 tasks with 5 second intervals (would take 50s real time)
        await service.execute_periodic_task(iterations=10, interval=5.0)

        # Completes instantly in test
        assert service.execution_count == 10

        # Time advanced by 50 seconds (10 intervals * 5 seconds)
        assert fake_time.current_seconds == 1000050

    @pytest.mark.asyncio
    async def test_service_with_production_defaults(self):
        """Service works with production defaults (real time)."""
        service = self.ServiceWithTime()  # Uses production defaults

        # Execute once with minimal interval
        await service.execute_periodic_task(iterations=1, interval=0.001)

        assert service.execution_count == 1
        assert service.last_execution is not None


class TestFractionalSeconds:
    """Tests for fractional second support."""

    def test_fractional_initial_time(self):
        """FakeTimeProvider supports fractional initial time."""
        fake_time = FakeTimeProvider(initial_seconds=1000000.123)
        assert fake_time.current_seconds == 1000000.123

    def test_fractional_advance(self):
        """advance() supports fractional seconds."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        fake_time.advance(0.5)
        assert fake_time.current_seconds == 1000000.5

    @pytest.mark.asyncio
    async def test_fractional_async_sleep(self):
        """async_sleep supports fractional durations."""
        fake_time = FakeTimeProvider(initial_seconds=1000000)
        await fake_time.async_sleep(0.123)
        assert fake_time.current_seconds == 1000000.123

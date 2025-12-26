"""Comprehensive unit tests for BackgroundTask base class."""

from unittest.mock import AsyncMock, Mock

import pytest

from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask
from csbot.utils.time import AsyncSleep, FakeTimeProvider, system_async_sleep
from tests.tasks.helpers import ExecutionTracker, wait_for_execution_count, wrap_task_with_tracker


class ConcreteBackgroundTask(BotInstanceBackgroundTask):
    """Concrete implementation for testing."""

    def __init__(
        self,
        bot,
        sleep_seconds=1.0,
        error_sleep_seconds=60.0,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        super().__init__(bot, async_sleep=async_sleep)
        self._sleep_seconds = sleep_seconds
        self._error_sleep_seconds = error_sleep_seconds
        self.should_raise_error = False
        self.error_to_raise = Exception("Test error")

    async def execute_tick(self) -> None:
        """Test implementation that can raise errors."""
        if self.should_raise_error:
            raise self.error_to_raise

    def get_sleep_seconds(self) -> float:
        """Return configured sleep seconds."""
        return self._sleep_seconds

    def get_error_sleep_seconds(self) -> float:
        """Return configured error sleep seconds."""
        return self._error_sleep_seconds


def make_concrete_task(bot, fake_time, sleep_seconds=1.0, error_sleep_seconds=60.0):
    """Create ConcreteBackgroundTask with fake time."""
    return ConcreteBackgroundTask(
        bot,
        sleep_seconds=sleep_seconds,
        error_sleep_seconds=error_sleep_seconds,
        async_sleep=fake_time.async_sleep,
    )


class TestBackgroundTask:
    """Comprehensive tests for BackgroundTask base class."""

    @pytest.fixture
    def fake_time(self):
        """Create fake time provider for testing."""
        return FakeTimeProvider(initial_seconds=1000000)

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot for testing."""
        bot = Mock()
        bot.logger = Mock()
        return bot

    @pytest.fixture
    def task(self, mock_bot, fake_time):
        """Create a concrete task instance for testing."""
        return make_concrete_task(mock_bot, fake_time)

    @pytest.mark.asyncio
    async def test_task_stop_when_not_started(self, task):
        """Test stopping a task that was never started is safe."""
        # Should not raise exception
        await task.stop()

        # Task should remain None
        assert task._task is None

    @pytest.mark.asyncio
    async def test_task_stop_already_stopped(self, task):
        """Test stopping an already stopped task is safe."""
        await task.start()
        await task.stop()

        # Stopping again should be safe
        await task.stop()

    @pytest.mark.asyncio
    async def test_error_handling_continues_execution(self, mock_bot, fake_time):
        """Test task continues running after errors."""
        task = make_concrete_task(mock_bot, fake_time, sleep_seconds=0.1, error_sleep_seconds=0.1)
        tracker = ExecutionTracker()
        wrap_task_with_tracker(task, tracker)

        # Configure to raise error on first execution
        task.should_raise_error = True

        await task.start()

        # Advance time for error to occur - execution will fail, tracker won't increment
        fake_time.advance(0.2)
        # Give event loop time to process the error
        await fake_time.sleep_and_yield(0)

        # Stop raising errors
        task.should_raise_error = False

        # Wait for successful executions after recovery
        fake_time.advance(0.3)
        await wait_for_execution_count(tracker, target=2, timeout=2.0)

        await task.stop()

        # Should have executed successfully at least twice after error recovery
        assert tracker.count >= 2

        # Error should have been logged
        task.bot.logger.error.assert_called()  # type: ignore

    @pytest.mark.asyncio
    async def test_custom_error_handler(self, mock_bot, fake_time):
        """Test custom error handler is called."""
        task = make_concrete_task(mock_bot, fake_time, sleep_seconds=0.05, error_sleep_seconds=0.05)

        # Mock the error handler
        task.on_error = AsyncMock()

        # Configure to raise error
        task.should_raise_error = True
        test_error = ValueError("Custom test error")
        task.error_to_raise = test_error

        await task.start()

        # Advance time for error to occur and be handled
        fake_time.advance(0.15)
        # Yield to let error handler run
        await fake_time.sleep_and_yield(0, yields=10)

        await task.stop()

        # Custom error handler should have been called at least once
        assert task.on_error.call_count >= 1
        # Check that it was called with the expected error
        assert any(call[0][0] == test_error for call in task.on_error.call_args_list)

    @pytest.mark.asyncio
    async def test_default_error_handler_logs(self, task):
        """Test default error handler logs errors correctly."""
        # Configure to raise error
        task.should_raise_error = True
        test_error = RuntimeError("Test runtime error")
        task.error_to_raise = test_error

        # Call error handler directly
        await task.on_error(test_error)

        # Should log error with exc_info
        task.bot.logger.error.assert_called_once_with(
            f"Error in {task.__class__.__name__}: {test_error}", exc_info=True
        )

    @pytest.mark.asyncio
    async def test_concurrent_task_operations(self, mock_bot, fake_time):
        """Test multiple tasks can run concurrently."""
        task1 = make_concrete_task(mock_bot, fake_time, sleep_seconds=0.1)
        task2 = make_concrete_task(mock_bot, fake_time, sleep_seconds=0.1)

        tracker1 = ExecutionTracker()
        tracker2 = ExecutionTracker()
        wrap_task_with_tracker(task1, tracker1)
        wrap_task_with_tracker(task2, tracker2)

        # Start both tasks
        await task1.start()
        await task2.start()

        # Advance time and wait for both to execute
        fake_time.advance(0.3)
        await wait_for_execution_count(tracker1, target=2, timeout=2.0)
        await wait_for_execution_count(tracker2, target=2, timeout=2.0)

        # Stop both tasks
        await task1.stop()
        await task2.stop()

        # Both should have executed
        assert tracker1.count >= 2
        assert tracker2.count >= 2

    @pytest.mark.asyncio
    async def test_task_state_transitions(self, task):
        """Test task state transitions are correct."""
        # Initial state
        assert task._task is None

        # After start
        await task.start()
        assert task._task is not None
        assert not task._task.done()

        # After stop
        await task.stop()
        assert task._task is not None
        assert task._task.done()

    def test_jitter_seconds(self, task):
        """Test jitter seconds works correctly."""
        import random

        random.seed(43)
        did_not_equal = False
        for _ in range(100):
            seconds = random.uniform(1, 100)
            jitter_seconds = random.randint(0, 50)
            jittered = task._jitter_seconds(seconds, jitter_seconds)
            if jittered != seconds:
                did_not_equal = True
                break
            assert jittered >= 0
            assert jittered <= seconds + jitter_seconds
            assert type(jittered) is float
        assert did_not_equal

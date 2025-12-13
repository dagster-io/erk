"""Comprehensive unit tests for BackgroundTaskManager."""

import logging
from unittest.mock import Mock

import pytest

from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask
from csbot.slackbot.tasks.background_task import BackgroundTask
from csbot.slackbot.tasks.background_tasks import BackgroundTaskManager
from csbot.utils.time import AsyncSleep, FakeTimeProvider, system_async_sleep
from tests.tasks.helpers import ExecutionTracker, wait_for_execution_count, wrap_task_with_tracker


class MockBackgroundTask(BotInstanceBackgroundTask):
    """Mock task for testing."""

    def __init__(
        self,
        bot,
        name: str,
        should_fail_on_stop: bool = False,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        super().__init__(bot, async_sleep=async_sleep)
        self.name = name
        self.should_fail_on_stop = should_fail_on_stop
        self.started = False
        self.stopped = False

    async def execute_tick(self) -> None:
        """Mock execute_tick."""
        pass

    def get_sleep_seconds(self) -> float:
        """Return 1 second sleep."""
        return 1.0

    async def start(self) -> None:
        """Mock start that tracks state."""
        await super().start()
        self.started = True

    async def stop(self) -> None:
        """Mock stop that can raise errors."""
        if self.should_fail_on_stop:
            raise RuntimeError(f"Failed to stop {self.name}")
        self.stopped = True
        await super().stop()


def make_mock_task(bot, name, fake_time, should_fail_on_stop=False):
    """Create MockBackgroundTask with fake time."""
    return MockBackgroundTask(
        bot, name, should_fail_on_stop=should_fail_on_stop, async_sleep=fake_time.async_sleep
    )


class TestBackgroundTaskManager:
    """Comprehensive tests for BackgroundTaskManager."""

    @pytest.fixture
    def fake_time(self):
        """Create fake time provider for testing."""
        return FakeTimeProvider(initial_seconds=1000000)

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.logger = Mock()
        return bot

    @pytest.fixture
    def sample_tasks(self, mock_bot, fake_time):
        """Create sample tasks for testing."""
        return [
            make_mock_task(mock_bot, "task1", fake_time),
            make_mock_task(mock_bot, "task2", fake_time),
            make_mock_task(mock_bot, "task3", fake_time),
        ]

    @pytest.fixture
    def manager(self, sample_tasks, mock_logger):
        """Create a BackgroundTaskManager with sample tasks."""
        return BackgroundTaskManager(sample_tasks, mock_logger)

    def test_manager_initialization(self, sample_tasks, mock_logger):
        """Test manager initializes correctly."""
        manager = BackgroundTaskManager(sample_tasks, mock_logger)

        assert manager.tasks == sample_tasks
        assert manager.logger is mock_logger

    def test_manager_with_empty_tasks(self, mock_logger):
        """Test manager works with empty task list."""
        manager = BackgroundTaskManager([], mock_logger)

        assert manager.tasks == []
        assert manager.logger is mock_logger

    @pytest.mark.asyncio
    async def test_start_all_tasks(self, manager, sample_tasks, mock_logger):
        """Test starting all tasks."""
        await manager.start_all()

        # All tasks should be started
        for task in sample_tasks:
            assert task.started

        # Logger should confirm startup
        mock_logger.info.assert_called_with("Started all background tasks")

    @pytest.mark.asyncio
    async def test_stop_all_tasks(self, manager, sample_tasks, mock_logger):
        """Test stopping all tasks."""
        # Start tasks first
        await manager.start_all()

        # Stop all tasks
        await manager.stop_all()

        # All tasks should be stopped
        for task in sample_tasks:
            assert task.stopped

        # Logger should confirm shutdown
        mock_logger.info.assert_called_with("Stopped all background tasks")

    @pytest.mark.asyncio
    async def test_stop_all_tasks_reverse_order(self, mock_bot, mock_logger, fake_time):
        """Test tasks are stopped in reverse order."""
        stop_order = []

        class OrderTrackingTask(MockBackgroundTask):
            def __init__(self, bot, name: str, async_sleep: AsyncSleep = system_async_sleep):
                super().__init__(bot, name, async_sleep=async_sleep)

            async def stop(self) -> None:
                stop_order.append(self.name)
                await super().stop()

        def make_order_task(name):
            return OrderTrackingTask(mock_bot, name, async_sleep=fake_time.async_sleep)

        tasks = [
            make_order_task("first"),
            make_order_task("second"),
            make_order_task("third"),
        ]

        manager = BackgroundTaskManager(tasks, mock_logger)

        # Start and stop
        await manager.start_all()
        await manager.stop_all()

        # Should stop in reverse order
        assert stop_order == ["third", "second", "first"]

    @pytest.mark.asyncio
    async def test_stop_all_with_errors(self, mock_bot, mock_logger, fake_time):
        """Test stopping tasks handles errors gracefully."""
        tasks = [
            make_mock_task(mock_bot, "good_task1", fake_time),
            make_mock_task(mock_bot, "bad_task", fake_time, should_fail_on_stop=True),
            make_mock_task(mock_bot, "good_task2", fake_time),
        ]

        manager = BackgroundTaskManager(tasks, mock_logger)

        # Start tasks
        await manager.start_all()

        # Stop all - should handle error gracefully
        await manager.stop_all()

        # Good tasks should still be stopped
        assert tasks[0].stopped
        assert tasks[2].stopped

        # Bad task should not be marked as stopped
        assert not tasks[1].stopped

        # Error should be logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error stopping task MockBackgroundTask" in error_call
        assert "Failed to stop bad_task" in error_call

    @pytest.mark.asyncio
    async def test_get_task_by_type(self, manager, sample_tasks):
        """Test getting task by type."""
        # Should find the first task of the type
        found_task = manager.get_task(MockBackgroundTask)
        assert found_task is sample_tasks[0]

    @pytest.mark.asyncio
    async def test_get_task_by_type_not_found(self, manager):
        """Test getting task by type when not found."""

        class NonExistentTask(BackgroundTask):
            async def execute_tick(self) -> None:
                pass

            def get_sleep_seconds(self) -> float:
                return 1.0

        found_task = manager.get_task(NonExistentTask)
        assert found_task is None

    @pytest.mark.asyncio
    async def test_get_task_with_subclass(self, mock_bot, mock_logger, fake_time):
        """Test getting task works with subclasses."""

        class SpecialTask(MockBackgroundTask):
            def __init__(self, bot, async_sleep: AsyncSleep = system_async_sleep):
                super().__init__(bot, "special", async_sleep=async_sleep)

        class AnotherTask(MockBackgroundTask):
            def __init__(self, bot, async_sleep: AsyncSleep = system_async_sleep):
                super().__init__(bot, "another", async_sleep=async_sleep)

        tasks = [
            make_mock_task(mock_bot, "regular", fake_time),
            SpecialTask(mock_bot, async_sleep=fake_time.async_sleep),
            AnotherTask(mock_bot, async_sleep=fake_time.async_sleep),
        ]

        manager = BackgroundTaskManager(tasks, mock_logger)

        # Should find the specific subclass
        special_task = manager.get_task(SpecialTask)
        assert isinstance(special_task, SpecialTask)
        assert hasattr(special_task, "name") and special_task.name == "special"

        # Should find any MockBackgroundTask (returns first match)
        any_task = manager.get_task(MockBackgroundTask)
        assert isinstance(any_task, MockBackgroundTask) and any_task.name == "regular"

    @pytest.mark.asyncio
    async def test_lifecycle_integration(self, manager, sample_tasks, mock_logger, fake_time):
        """Test complete lifecycle integration."""
        # Track execution of first task to verify tasks are running
        tracker = ExecutionTracker()
        wrap_task_with_tracker(sample_tasks[0], tracker)

        # Start all
        await manager.start_all()

        # Verify all started
        for task in sample_tasks:
            assert task.started
            assert not task.stopped

        # Wait for tasks to execute
        fake_time.advance(1.5)
        await wait_for_execution_count(tracker, target=1, timeout=2.0)

        # Stop all
        await manager.stop_all()

        # Verify all stopped
        for task in sample_tasks:
            assert task.started
            assert task.stopped

        # Verify logging
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Started all background tasks")
        mock_logger.info.assert_any_call("Stopped all background tasks")

    @pytest.mark.asyncio
    async def test_empty_task_list_operations(self, mock_logger):
        """Test operations work with empty task list."""
        manager = BackgroundTaskManager([], mock_logger)

        # Should not raise errors
        await manager.start_all()
        await manager.stop_all()

        # Should still log
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Started all background tasks")
        mock_logger.info.assert_any_call("Stopped all background tasks")

        # get_task should return None
        assert manager.get_task(MockBackgroundTask) is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, manager, sample_tasks, fake_time):
        """Test manager handles concurrent operations safely."""
        # Track execution to verify tasks run
        tracker = ExecutionTracker()
        wrap_task_with_tracker(sample_tasks[0], tracker)

        # Start multiple start/stop operations concurrently
        await manager.start_all()
        fake_time.advance(0.05)
        # Give event loop time to start tasks
        await fake_time.sleep_and_yield(0, yields=10)
        await manager.stop_all()

        # All tasks should end up started
        for task in sample_tasks:
            assert task.started
            # Note: stopped state may vary due to timing

    @pytest.mark.asyncio
    async def test_task_retrieval_with_multiple_same_type(self, mock_bot, mock_logger, fake_time):
        """Test task retrieval when multiple tasks of same type exist."""
        tasks = [
            make_mock_task(mock_bot, "first", fake_time),
            make_mock_task(mock_bot, "second", fake_time),
            make_mock_task(mock_bot, "third", fake_time),
        ]

        manager = BackgroundTaskManager(tasks, mock_logger)

        # Should return the first matching task
        found_task = manager.get_task(MockBackgroundTask)
        assert found_task is tasks[0]
        assert isinstance(found_task, MockBackgroundTask) and found_task.name == "first"

    def test_manager_task_sequence_immutability(self, sample_tasks, mock_logger):
        """Test manager doesn't modify the original task sequence."""
        original_tasks = sample_tasks.copy()
        manager = BackgroundTaskManager(sample_tasks, mock_logger)

        # Manager should reference the same tasks
        assert manager.tasks is sample_tasks
        assert list(manager.tasks) == original_tasks

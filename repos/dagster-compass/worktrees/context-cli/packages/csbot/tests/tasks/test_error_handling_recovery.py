"""Comprehensive error handling and recovery test scenarios for background tasks."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask
from csbot.slackbot.tasks.background_tasks import BackgroundTaskManager
from csbot.utils.time import AsyncSleep, FakeTimeProvider, system_async_sleep
from tests.tasks.helpers import wait_for_condition


class FailingTask(BotInstanceBackgroundTask):
    """Task that can be configured to fail in various ways."""

    def __init__(self, bot, fail_mode: str = "none", async_sleep: AsyncSleep = system_async_sleep):
        super().__init__(bot, async_sleep=async_sleep)
        self.fail_mode = fail_mode
        self.execution_count = 0
        self.error_count = 0

    async def execute_tick(self) -> None:
        """Execute with configurable failure modes."""
        self.execution_count += 1

        if self.fail_mode == "always":
            raise RuntimeError(f"Always failing task - execution {self.execution_count}")
        elif self.fail_mode == "intermittent" and self.execution_count % 2 == 0:
            raise ValueError(f"Intermittent failure - execution {self.execution_count}")
        elif self.fail_mode == "after_n" and self.execution_count > 3:
            raise ConnectionError(f"Failed after 3 executions - execution {self.execution_count}")

    def get_sleep_seconds(self) -> float:
        """Short sleep for testing."""
        return 0.05

    def get_error_sleep_seconds(self) -> float:
        """Short error sleep for testing."""
        return 0.05

    async def on_error(self, error: Exception) -> None:
        """Track error occurrences."""
        self.error_count += 1
        await super().on_error(error)


class RecoveryTask(BotInstanceBackgroundTask):
    """Task that recovers after a certain number of failures."""

    def __init__(
        self,
        bot,
        failures_before_recovery: int = 3,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        super().__init__(bot, async_sleep=async_sleep)
        self.failures_before_recovery = failures_before_recovery
        self.execution_count = 0
        self.error_count = 0

    async def execute_tick(self) -> None:
        """Fail for a while, then recover."""
        self.execution_count += 1

        if self.error_count < self.failures_before_recovery:
            raise RuntimeError(f"Still failing - error {self.error_count + 1}")

    def get_sleep_seconds(self) -> float:
        return 0.05

    def get_error_sleep_seconds(self) -> float:
        return 0.05

    async def on_error(self, error: Exception) -> None:
        """Track errors and allow recovery."""
        self.error_count += 1
        await super().on_error(error)


def make_failing_task(bot, fake_time, fail_mode="none"):
    """Create FailingTask with fake time."""
    return FailingTask(bot, fail_mode=fail_mode, async_sleep=fake_time.async_sleep)


def make_recovery_task(bot, fake_time, failures_before_recovery=3):
    """Create RecoveryTask with fake time."""
    return RecoveryTask(
        bot, failures_before_recovery=failures_before_recovery, async_sleep=fake_time.async_sleep
    )


class TestTaskErrorHandling:
    """Test error handling scenarios for individual tasks."""

    @pytest.fixture
    def fake_time(self):
        """Create fake time provider for testing."""
        return FakeTimeProvider(initial_seconds=1000000)

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.logger = Mock()
        return bot

    @pytest.mark.asyncio
    async def test_task_continues_after_errors(self, mock_bot, fake_time):
        """Test that tasks continue running after encountering errors."""
        task = make_failing_task(mock_bot, fake_time, fail_mode="intermittent")

        await task.start()

        # Wait for multiple execution cycles
        fake_time.advance(0.5)
        await wait_for_condition(lambda: task.execution_count >= 5, timeout=2.0)

        await task.stop()

        # Should have executed multiple times and encountered some errors
        assert task.execution_count >= 5
        assert task.error_count >= 2  # Intermittent mode fails on even executions

        # Should continue executing despite errors
        assert task.execution_count > task.error_count

    @pytest.mark.asyncio
    async def test_task_error_sleep_timing(self, mock_bot, fake_time):
        """Test that tasks respect error sleep timing."""
        task = make_failing_task(mock_bot, fake_time, fail_mode="always")
        task.get_error_sleep_seconds = lambda: 0.1  # Override for testing

        await task.start()

        # Wait for error cycles
        fake_time.advance(0.3)
        await wait_for_condition(lambda: task.error_count >= 2, timeout=2.0)

        await task.stop()

        # Should have attempted multiple error cycles (0.3s / 0.1s error sleep = ~3 cycles)
        assert task.error_count >= 2

    @pytest.mark.asyncio
    async def test_task_recovery_after_failures(self, mock_bot, fake_time):
        """Test that tasks can recover after a series of failures."""
        task = make_recovery_task(mock_bot, fake_time, failures_before_recovery=3)

        await task.start()

        # Wait for recovery and subsequent successful executions
        fake_time.advance(0.4)
        await wait_for_condition(lambda: task.execution_count > 3, timeout=2.0)

        await task.stop()

        # Should have failed exactly the specified number of times, then recovered
        assert task.error_count == 3
        assert task.execution_count > 3  # Should continue executing after recovery

    @pytest.mark.asyncio
    async def test_custom_error_handler_called(self, mock_bot, fake_time):
        """Test that custom error handlers are properly invoked."""
        task = make_failing_task(mock_bot, fake_time, fail_mode="always")
        custom_error_handler = AsyncMock()
        task.on_error = custom_error_handler

        await task.start()
        fake_time.advance(0.3)
        # Wait for error handler to be called
        await wait_for_condition(lambda: custom_error_handler.call_count >= 1, timeout=2.0)
        await task.stop()

        # Custom error handler should have been called
        assert custom_error_handler.call_count >= 1

        # Should have been called with the error
        call_args = custom_error_handler.call_args_list[0][0]
        assert len(call_args) == 1
        assert isinstance(call_args[0], RuntimeError)

    @pytest.mark.asyncio
    async def test_error_logging_behavior(self, mock_bot, fake_time):
        """Test that errors are properly logged."""
        task = make_failing_task(mock_bot, fake_time, fail_mode="always")

        await task.start()
        fake_time.advance(0.3)
        # Wait for logger to be called
        await wait_for_condition(lambda: mock_bot.logger.error.call_count >= 1, timeout=2.0)
        await task.stop()

        # Should have logged errors
        assert mock_bot.logger.error.call_count >= 1

        # Check error message format
        error_call = mock_bot.logger.error.call_args_list[0]
        error_message = error_call[0][0]
        assert "Error in FailingTask" in error_message
        assert "Always failing task" in error_message

        # Should have called with exc_info=True
        assert error_call[1]["exc_info"] is True


class TestTaskManagerErrorHandling:
    """Test error handling in BackgroundTaskManager."""

    @pytest.fixture
    def fake_time(self):
        """Create fake time provider for testing."""
        return FakeTimeProvider(initial_seconds=1000000)

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.logger = Mock()
        return bot

    @pytest.mark.asyncio
    async def test_manager_handles_task_start_failures(self, mock_bot, mock_logger, fake_time):
        """Test manager handles individual task start failures gracefully."""

        class FailingStartTask(BotInstanceBackgroundTask):
            def __init__(
                self, bot, should_fail: bool = False, async_sleep: AsyncSleep = system_async_sleep
            ):
                super().__init__(bot, async_sleep=async_sleep)
                self.should_fail = should_fail

            async def start(self) -> None:
                if self.should_fail:
                    raise RuntimeError("Failed to start task")
                await super().start()

            async def execute_tick(self) -> None:
                pass

            def get_sleep_seconds(self) -> float:
                return 1.0

        def make_failing_start_task(should_fail=False):
            return FailingStartTask(
                mock_bot, should_fail=should_fail, async_sleep=fake_time.async_sleep
            )

        good_task = make_failing_start_task(should_fail=False)
        bad_task = make_failing_start_task(should_fail=True)
        another_good_task = make_failing_start_task(should_fail=False)

        manager = BackgroundTaskManager([good_task, bad_task, another_good_task], mock_logger)

        # Should raise exception from the failing task
        with pytest.raises(RuntimeError, match="Failed to start task"):
            await manager.start_all()

        # Clean up any started tasks
        await manager.stop_all()

    @pytest.mark.asyncio
    async def test_manager_handles_task_stop_failures_gracefully(
        self, mock_bot, mock_logger, fake_time
    ):
        """Test manager continues stopping other tasks even if some fail to stop."""

        class FailingStopTask(BotInstanceBackgroundTask):
            def __init__(
                self,
                bot,
                name: str,
                should_fail_stop: bool = False,
                async_sleep: AsyncSleep = system_async_sleep,
            ):
                super().__init__(bot, async_sleep=async_sleep)
                self.name = name
                self.should_fail_stop = should_fail_stop
                self.stopped = False

            async def stop(self) -> None:
                if self.should_fail_stop:
                    raise RuntimeError(f"Failed to stop {self.name}")
                self.stopped = True
                await super().stop()

            async def execute_tick(self) -> None:
                pass

            def get_sleep_seconds(self) -> float:
                return 1.0

        def make_failing_stop_task(name, should_fail_stop=False):
            return FailingStopTask(
                mock_bot, name, should_fail_stop=should_fail_stop, async_sleep=fake_time.async_sleep
            )

        good_task1 = make_failing_stop_task("good1", should_fail_stop=False)
        bad_task = make_failing_stop_task("bad", should_fail_stop=True)
        good_task2 = make_failing_stop_task("good2", should_fail_stop=False)

        manager = BackgroundTaskManager([good_task1, bad_task, good_task2], mock_logger)

        # Start all tasks
        await manager.start_all()

        # Stop all - should handle the failing task gracefully
        await manager.stop_all()

        # Good tasks should be stopped
        assert good_task1.stopped
        assert good_task2.stopped

        # Bad task should not be marked as stopped
        assert not bad_task.stopped

        # Error should be logged
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "Error stopping task FailingStopTask" in error_message
        assert "Failed to stop bad" in error_message


class TestRealWorldErrorScenarios:
    """Test error scenarios based on real-world failure modes."""

    @pytest.fixture
    def fake_time(self):
        """Create fake time provider for testing."""
        return FakeTimeProvider(initial_seconds=1000000)

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.logger = Mock()
        bot.agent = Mock()
        bot.send_simple_governance_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_dataset_monitor(self):
        """Create a mock dataset monitor."""
        monitor = Mock()
        monitor.update_repository = AsyncMock()
        monitor.discover_all_datasets = AsyncMock()
        monitor.check_and_update_dataset_if_changed = AsyncMock()
        return monitor

    @pytest.mark.asyncio
    async def test_task_resource_cleanup_on_error(self, mock_bot, fake_time):
        # test that even after failure the task keeps running
        event = asyncio.Event()

        class ResourceTask(BotInstanceBackgroundTask):
            def __init__(self, bot, async_sleep: AsyncSleep = system_async_sleep):
                super().__init__(bot, async_sleep=async_sleep)
                self.failures = 0

            async def execute_tick(self) -> None:
                if self.failures == 0:
                    self.failures += 1
                    # Don't release on error to test cleanup
                    raise RuntimeError("Simulated failure")

                event.set()

            def get_sleep_seconds(self) -> float:
                return 0.05

            def get_error_sleep_seconds(self) -> float:
                return 0.05

        task = ResourceTask(mock_bot, async_sleep=fake_time.async_sleep)

        await task.start()
        async with asyncio.timeout(delay=2):
            await event.wait()
        await task.stop()

        assert task.failures > 0

    @pytest.mark.asyncio
    async def test_cascading_error_scenarios(self, mock_bot, fake_time):
        """Test handling of cascading errors across multiple tasks."""

        class DependentTask(BotInstanceBackgroundTask):
            def __init__(
                self,
                bot,
                name: str,
                dependency_task=None,
                async_sleep: AsyncSleep = system_async_sleep,
            ):
                super().__init__(bot, async_sleep=async_sleep)
                self.name = name
                self.dependency_task = dependency_task
                self.execution_count = 0
                self.should_fail = False  # Add this attribute to the class

            async def execute_tick(self) -> None:
                self.execution_count += 1

                # If dependency is failing, this task fails too
                if (
                    self.dependency_task
                    and hasattr(self.dependency_task, "should_fail")
                    and self.dependency_task.should_fail
                ):
                    raise RuntimeError(f"{self.name} failed due to dependency failure")

            def get_sleep_seconds(self) -> float:
                return 0.05

        def make_dependent_task(name, dependency_task=None):
            return DependentTask(
                mock_bot, name, dependency_task=dependency_task, async_sleep=fake_time.async_sleep
            )

        # Create dependency chain
        primary_task = make_dependent_task("primary")
        dependent_task = make_dependent_task("dependent", dependency_task=primary_task)

        # Make primary task fail
        primary_task.should_fail = True

        # Create a mock logger for the manager
        mock_logger = Mock()
        manager = BackgroundTaskManager([primary_task, dependent_task], mock_logger)

        await manager.start_all()
        fake_time.advance(0.3)
        # Wait for both tasks to execute
        await wait_for_condition(
            lambda: primary_task.execution_count >= 1 and dependent_task.execution_count >= 1,
            timeout=2.0,
        )
        await manager.stop_all()

        # Both tasks should have attempted execution
        assert primary_task.execution_count >= 1
        assert dependent_task.execution_count >= 1

        # Both tasks should have logged errors to their respective bot loggers
        # Since both tasks use the same mock_bot, we check the total error count
        assert mock_bot.logger.error.call_count >= 1

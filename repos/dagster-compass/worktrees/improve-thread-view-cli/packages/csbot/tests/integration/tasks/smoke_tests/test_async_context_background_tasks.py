"""Smoke tests to catch 'Cannot run in async context' errors in background tasks."""

from unittest.mock import AsyncMock, Mock

import pytest

from csbot.slackbot.channel_bot.tasks.cron_scheduler import CronJobSchedulerTask
from csbot.slackbot.channel_bot.tasks.github_monitor import GitHubMonitorTask
from csbot.slackbot.channel_bot.tasks.weekly_refresh import WeeklyRefreshTask
from tests.factories.context_store_factory import context_store_builder


class TestBackgroundTasksAsyncContext:
    """Smoke tests for async context errors in all background tasks."""

    @pytest.mark.asyncio
    async def test_weekly_refresh_task_executes_without_async_context_error(self):
        """Smoke test: WeeklyRefreshTask should not throw async context errors."""
        # Mock dependencies
        bot = Mock()
        dataset_monitor = Mock()
        github_pr_handler = Mock()

        # Configure bot.load_context_store to return empty datasets
        empty_context_store = context_store_builder().with_project("test/project").build()
        bot.load_context_store = AsyncMock(return_value=empty_context_store)
        bot.logger = Mock()

        task = WeeklyRefreshTask(bot, dataset_monitor, github_pr_handler)

        # This should complete without "Cannot run in async context" error
        await task.execute_tick()

        bot.logger.info.assert_called_with("No datasets found for weekly refresh")

    @pytest.mark.asyncio
    async def test_cron_scheduler_task_executes_without_async_context_error(self):
        """Smoke test: CronJobSchedulerTask should not throw async context errors."""
        # Mock dependencies
        bot = Mock()
        cron_handler = Mock()

        # Configure mocks to return empty cron jobs to short-circuit execution
        bot.csbot_client.get_cron_jobs = AsyncMock(return_value={})
        cron_handler.find_next_due_job = Mock(return_value=None)  # No job due
        cron_handler.get_default_sleep_seconds = Mock(return_value=60)

        task = CronJobSchedulerTask(bot, cron_handler)

        # This should complete without "Cannot run in async context" error
        await task.execute_tick()

        bot.csbot_client.get_cron_jobs.assert_called_once()
        cron_handler.find_next_due_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_github_monitor_task_executes_without_async_context_error(self):
        """Smoke test: GitHubMonitorTask should not throw async context errors."""
        # Mock dependencies
        bot = Mock()
        bot.github_monitor.tick = AsyncMock()

        task = GitHubMonitorTask(bot)

        # This should complete without "Cannot run in async context" error
        await task.execute_tick()

        bot.github_monitor.tick.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_background_tasks_execute_without_async_context_errors(self):
        """Integration smoke test: All background tasks should execute without async context errors."""

        # Mock bot with all required dependencies
        bot = Mock()
        bot.logger = Mock()
        bot.key = Mock()
        bot.key.channel_name = "test-channel"
        bot.kv_store = Mock()
        bot.kv_store.get_channel_id = AsyncMock(
            return_value=None
        )  # Short-circuit daily exploration
        bot.agent = Mock()
        bot.agent.generate_structured_response = AsyncMock(return_value=Mock(analysis="Test"))
        bot.csbot_client.get_cron_jobs = AsyncMock(return_value={})
        bot.csbot_client.get_connection_names = AsyncMock(return_value=[])
        bot.send_daily_exploration = AsyncMock()
        bot.github_monitor.tick = AsyncMock()

        # Configure bot.load_context_store for WeeklyRefreshTask
        empty_context_store = context_store_builder().with_project("test/project").build()
        bot.load_context_store = AsyncMock(return_value=empty_context_store)

        # Mock dataset monitor
        dataset_monitor = Mock()
        dataset_monitor.check_and_update_dataset_if_changed = AsyncMock()

        # Mock other handlers
        github_pr_handler = Mock()
        cron_handler = Mock()
        cron_handler.find_next_due_job = Mock(return_value=None)  # No job due
        cron_handler.get_default_sleep_seconds = Mock(return_value=60)

        # Test each task type
        tasks = [
            WeeklyRefreshTask(bot, dataset_monitor, github_pr_handler),
            CronJobSchedulerTask(bot, cron_handler),
            GitHubMonitorTask(bot),
        ]

        for task in tasks:
            try:
                await task.execute_tick()
            except Exception as e:
                # Should not fail with async context error
                assert "Cannot run in async context" not in str(e), (
                    f"{task.__class__.__name__} failed with async context error: {e}"
                )
                # Other errors are acceptable for smoke test purposes
                # (missing mocks, etc. are expected in isolated testing)

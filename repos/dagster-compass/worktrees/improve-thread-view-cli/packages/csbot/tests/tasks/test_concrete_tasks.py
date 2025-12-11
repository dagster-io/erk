"""Individual behavior tests for each concrete background task."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from csbot.slackbot.channel_bot.tasks.cron_scheduler import CronJobSchedulerTask
from csbot.slackbot.channel_bot.tasks.github_monitor import GitHubMonitorTask
from csbot.slackbot.channel_bot.tasks.weekly_refresh import WeeklyRefreshTask
from tests.factories.context_store_factory import context_store_builder


class TestCronJobSchedulerTask:
    """Tests for CronJobSchedulerTask behavior."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot with required dependencies."""
        bot = Mock()
        bot.logger = Mock()
        bot.csbot_client = Mock()
        bot.kv_store = Mock()
        bot.key = Mock()
        bot.key.channel_name = "test-channel"
        bot.send_simple_governance_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_cron_handler(self):
        """Create mock cron job handler."""
        handler = Mock()
        handler.find_next_due_job = Mock()
        handler.execute_cron_job = AsyncMock()
        handler.get_default_sleep_seconds = Mock(return_value=60)
        return handler

    @pytest.fixture
    def task(self, mock_bot, mock_cron_handler):
        """Create CronJobSchedulerTask for testing."""
        return CronJobSchedulerTask(mock_bot, mock_cron_handler)

    @pytest.mark.asyncio
    async def test_no_cron_jobs_available(self, task, mock_bot, mock_cron_handler):
        """Test behavior when no cron jobs are available."""
        mock_bot.csbot_client.get_cron_jobs = AsyncMock(return_value={})
        mock_cron_handler.find_next_due_job.return_value = None

        await task.execute_tick()

        mock_bot.csbot_client.get_cron_jobs.assert_called_once()
        mock_cron_handler.find_next_due_job.assert_called_once_with({})
        mock_cron_handler.execute_cron_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_cron_job_execution_success(self, task, mock_bot, mock_cron_handler):
        """Test successful cron job execution."""
        # Setup mocks
        cron_jobs = {"test_job": Mock()}
        mock_bot.csbot_client.get_cron_jobs = AsyncMock(return_value=cron_jobs)
        mock_cron_handler.find_next_due_job.return_value = ("test_job", cron_jobs["test_job"], 0)
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")

        await task.execute_tick()

        # Verify execution flow
        mock_bot.csbot_client.get_cron_jobs.assert_called()
        mock_cron_handler.execute_cron_job.assert_called_once_with("C123456", "test_job")
        mock_bot.logger.info.assert_called_with("Successfully executed cron job 'test_job'")

    @pytest.mark.asyncio
    async def test_cron_job_disappeared_before_execution(self, task, mock_bot, mock_cron_handler):
        """Test handling when cron job disappears before execution."""
        # First call returns job, second call (double-check) returns empty
        mock_bot.csbot_client.get_cron_jobs = AsyncMock(
            side_effect=[
                {"test_job": Mock()},
                {},  # Job disappeared
            ]
        )
        mock_cron_handler.find_next_due_job.return_value = ("test_job", Mock(), 0)

        await task.execute_tick()

        # Should not execute job
        mock_cron_handler.execute_cron_job.assert_not_called()
        mock_bot.logger.info.assert_called_with("Cron job 'test_job' disappeared, skipping")

    @pytest.mark.asyncio
    async def test_no_channel_found_error(self, task, mock_bot, mock_cron_handler):
        """Test error handling when channel is not found."""
        cron_jobs = {"test_job": Mock()}
        mock_bot.csbot_client.get_cron_jobs = AsyncMock(return_value=cron_jobs)
        mock_cron_handler.find_next_due_job.return_value = ("test_job", cron_jobs["test_job"], 0)
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value=None)

        await task.execute_tick()

        mock_cron_handler.execute_cron_job.assert_not_called()
        mock_bot.logger.error.assert_called_with("No channel found for cron job 'test_job'")

    @pytest.mark.asyncio
    async def test_cron_job_execution_error(self, task, mock_bot, mock_cron_handler):
        """Test error handling during cron job execution."""
        cron_jobs = {"test_job": Mock()}
        mock_bot.csbot_client.get_cron_jobs = AsyncMock(return_value=cron_jobs)
        mock_cron_handler.find_next_due_job.return_value = ("test_job", cron_jobs["test_job"], 0)
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")

        test_error = RuntimeError("Execution failed")
        mock_cron_handler.execute_cron_job.side_effect = test_error

        await task.execute_tick()

        mock_bot.logger.error.assert_called_with(
            "Error executing cron job 'test_job': Execution failed", exc_info=True
        )
        mock_bot.send_simple_governance_message.assert_called_once()

    def test_get_sleep_seconds(self, task, mock_cron_handler):
        """Test get_sleep_seconds delegates to handler."""
        result = task.get_sleep_seconds()

        assert result == 60
        mock_cron_handler.get_default_sleep_seconds.assert_called_once()


class TestGitHubMonitorTask:
    """Tests for GitHubMonitorTask behavior."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot with github_monitor."""
        bot = Mock()
        bot.github_monitor = Mock()
        bot.github_monitor.tick = AsyncMock()
        return bot

    @pytest.fixture
    def task(self, mock_bot):
        """Create GitHubMonitorTask for testing."""
        task = GitHubMonitorTask(mock_bot)
        task._jitter_seconds = lambda sleep_seconds, jitter_seconds: sleep_seconds
        return task

    @pytest.mark.asyncio
    async def test_execute_tick_delegates_to_github_monitor(self, task, mock_bot):
        """Test execute_tick delegates to github_monitor.tick()."""
        await task.execute_tick()

        mock_bot.github_monitor.tick.assert_called_once()

    def test_get_sleep_seconds(self, task):
        """Test sleep interval is 60 seconds."""
        assert task.get_sleep_seconds() == 60


class TestWeeklyRefreshTask:
    """Tests for WeeklyRefreshTask behavior."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot with required dependencies."""
        bot = Mock()
        bot.logger = Mock()
        bot.local_context_store = Mock()
        bot.profile = Mock()
        bot.agent = Mock()
        bot.send_simple_governance_message = AsyncMock()

        # load_context_store should return an empty ContextStore by default
        empty_context_store = context_store_builder().with_project("test/project").build()
        bot.load_context_store = AsyncMock(return_value=empty_context_store)
        return bot

    @pytest.fixture
    def mock_dataset_monitor(self):
        """Create mock dataset monitor."""
        monitor = Mock()
        monitor.update_repository = AsyncMock()
        monitor.discover_all_datasets = AsyncMock()
        return monitor

    @pytest.fixture
    def mock_github_pr_handler(self):
        """Create mock GitHub PR handler."""
        handler = Mock()
        handler.create_weekly_refresh_pr = AsyncMock()
        return handler

    @pytest.fixture
    def task(self, mock_bot, mock_dataset_monitor, mock_github_pr_handler):
        """Create WeeklyRefreshTask for testing."""
        task = WeeklyRefreshTask(mock_bot, mock_dataset_monitor, mock_github_pr_handler)
        task._jitter_seconds = lambda sleep_seconds, jitter_seconds: sleep_seconds
        return task

    @pytest.mark.asyncio
    async def test_no_datasets_found(
        self, task, mock_bot, mock_dataset_monitor, mock_github_pr_handler
    ):
        """Test behavior when no datasets are found."""
        # bot.load_context_store already returns empty datasets from fixture

        await task.execute_tick()

        # Should not create PR when no datasets
        mock_github_pr_handler.create_weekly_refresh_pr.assert_not_called()

        mock_bot.logger.info.assert_called_with("No datasets found for weekly refresh")

    @pytest.mark.asyncio
    async def test_successful_weekly_refresh(
        self, task, mock_bot, mock_dataset_monitor, mock_github_pr_handler
    ):
        """Test successful weekly refresh execution."""
        from csbot.contextengine.contextstore_protocol import (
            Dataset,
        )

        # Create test datasets
        dataset1 = Dataset(table_name="table1", connection="test_conn")
        dataset2 = Dataset(table_name="table2", connection="test_conn")

        # Mock load_context_store to return datasets
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .add_dataset(dataset1)
            .add_dataset(dataset2)
            .build()
        )
        mock_bot.load_context_store = AsyncMock(return_value=context_store)

        await task.execute_tick()

        # Should create PR with datasets and project
        mock_github_pr_handler.create_weekly_refresh_pr.assert_called_once()
        call_kwargs = mock_github_pr_handler.create_weekly_refresh_pr.call_args.kwargs
        assert set(call_kwargs["datasets"]) == {dataset1, dataset2}
        assert call_kwargs["profile"] == mock_bot.profile
        assert call_kwargs["agent"] == mock_bot.agent
        assert call_kwargs["logger"] == mock_bot.logger

    def test_get_sleep_seconds_calculates_next_sunday_11pm(self, task, mock_bot):
        """Test sleep calculation for next Sunday at 11 PM."""
        with patch("csbot.slackbot.channel_bot.tasks.weekly_refresh.datetime") as mock_datetime:
            # Mock Wednesday at 2 PM
            current_time = datetime(2024, 1, 17, 14, 0, 0)  # Wednesday
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            sleep_seconds = task.get_sleep_seconds()

            # Wednesday (2) to Sunday (6) = 4 days, plus time until 11 PM
            # 4 days = 4 * 24 * 3600 = 345600 seconds
            # 14:00 to 23:00 = 9 hours = 32400 seconds
            # Total = 345600 + 32400 = 378000 seconds
            expected_seconds = 4 * 24 * 3600 + 9 * 3600
            assert sleep_seconds == expected_seconds

    def test_get_sleep_seconds_next_week_when_past_sunday_11pm(self, task, mock_bot):
        """Test sleep calculation when current time is past Sunday 11 PM."""
        with patch("csbot.slackbot.channel_bot.tasks.weekly_refresh.datetime") as mock_datetime:
            # Mock Sunday at 11:30 PM (past execution time)
            current_time = datetime(2024, 1, 21, 23, 30, 0)  # Sunday 11:30 PM
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            sleep_seconds = task.get_sleep_seconds()

            # Should wait until next Sunday 11 PM (7 days minus 30 minutes)
            expected_seconds = 7 * 24 * 3600 - 30 * 60  # 7 days - 30 minutes
            assert sleep_seconds == expected_seconds

    @pytest.mark.asyncio
    async def test_on_error_sends_governance_message(self, task, mock_bot):
        """Test error handling sends governance message."""
        test_error = RuntimeError("Weekly refresh failed")

        await task.on_error(test_error)

        mock_bot.send_simple_governance_message.assert_called_once_with(
            "⚠️ *Error in weekly dataset refresh:* Weekly refresh failed"
        )

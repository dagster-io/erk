"""Tests for DailyExplorationTask Temporal workflow reconciliation and execution."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from temporalio.client import ScheduleCalendarSpec, ScheduleSpec
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from csbot.slackbot.channel_bot.tasks.daily_exploration import DailyExplorationTask
from csbot.slackbot.storage.onboarding_state import BotInstanceType
from csbot.temporal.daily_exploration.activity import (
    DailyExplorationActivity,
    DailyExplorationInput,
    DailyExplorationStatus,
    DailyExplorationSuccess,
)
from csbot.temporal.daily_exploration.workflow import (
    DailyExplorationWorkflow,
    DailyExplorationWorkflowInput,
)


class TestDailyExplorationTaskReconciliation:
    """Tests for DailyExplorationTask Temporal schedule reconciliation."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot with required dependencies."""
        bot = Mock()
        bot.logger = Mock()
        bot.key = Mock()
        bot.key.channel_name = "daily-channel"
        bot.key.to_bot_id = Mock(return_value="T123-daily-channel")
        bot.temporal_client = Mock()
        bot.temporal_client.get_schedule_handle = Mock()
        bot.temporal_client.create_schedule = AsyncMock()
        # Mock bot_config
        bot.bot_config = Mock()
        bot.bot_config.organization_type = BotInstanceType.STANDARD
        bot.bot_config.is_prospector = False
        bot.bot_config.organization_id = 1
        # Mock bot_server with temporal config
        bot.bot_server = Mock()
        bot.bot_server.config = Mock()
        bot.bot_server.config.temporal = Mock()
        bot.bot_server.config.temporal.task_queue = "test-task-queue"
        bot.bot_background_task_manager = AsyncMock()
        return bot

    @pytest.fixture
    def task(self, mock_bot):
        """Create DailyExplorationTask for testing."""
        return DailyExplorationTask(mock_bot)

    @pytest.mark.asyncio
    async def test_creates_schedule_when_not_exists(self, task, mock_bot):
        """Test that task creates Temporal schedule when it doesn't exist."""
        # Mock schedule doesn't exist - describe() raises RPCError with NOT_FOUND status
        mock_schedule_handle = Mock()
        mock_schedule_handle.describe = AsyncMock(
            side_effect=RPCError("not found", RPCStatusCode.NOT_FOUND, b"")
        )
        mock_bot.temporal_client.get_schedule_handle.return_value = mock_schedule_handle

        await task.execute_tick()

        # Verify schedule creation
        mock_bot.bot_background_task_manager.reconcile.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_reconciliation_when_exempt(self, task, mock_bot):
        """Test that task skips reconciliation for exempt organizations."""
        with patch(
            "csbot.slackbot.channel_bot.tasks.daily_exploration.is_exempt_from_daily_exploration"
        ) as mock_exempt:
            mock_exempt.return_value = True

            await task.execute_tick()

            # Should not interact with Temporal
            mock_bot.temporal_client.get_schedule_handle.assert_not_called()
            mock_bot.temporal_client.create_schedule.assert_not_called()

    def test_schedule_spec_configuration(self, task):
        """Test that schedule spec is correctly configured."""
        spec = task.get_schedule_spec()

        assert isinstance(spec, ScheduleSpec)
        assert len(spec.calendars) == 1

        calendar = spec.calendars[0]
        assert isinstance(calendar, ScheduleCalendarSpec)

        # Check hour (9 AM)
        assert len(calendar.hour) == 1
        assert calendar.hour[0].start == 9
        assert calendar.hour[0].end == 9

        # Check day of week (Monday-Friday)
        assert len(calendar.day_of_week) == 1
        assert calendar.day_of_week[0].start == 1  # Monday
        assert calendar.day_of_week[0].end == 5  # Friday

        # Check jitter (1 hour)
        assert spec.jitter == timedelta(hours=1)

    def test_workflow_args(self, task, mock_bot):
        """Test that workflow args are correctly configured."""
        args = task.get_workflow_args()

        # Should be a list with one DailyExplorationWorkflowInput
        assert len(args) == 1
        workflow_input = args[0]
        assert isinstance(workflow_input, DailyExplorationWorkflowInput)
        assert workflow_input.bot_id == "T123-daily-channel"
        assert workflow_input.channel_name == "daily-channel"

    def test_schedule_id(self, task):
        """Test schedule ID format."""
        schedule_id = task.get_schedule_id()
        assert schedule_id == "daily-exploration-T123-daily-channel"

    def test_workflow_id_prefix(self, task):
        """Test workflow ID prefix."""
        workflow_id = task.get_workflow_id_prefix()
        assert workflow_id == "daily-exploration-T123-daily-channel"

    def test_workflow_type(self, task):
        """Test workflow type name."""
        from csbot.temporal.constants import Workflow

        workflow_type = task.get_workflow_type()
        assert workflow_type == Workflow.DAILY_EXPLORATION_WORKFLOW_NAME

    def test_get_sleep_seconds(self, task):
        """Test sleep interval is 1 hour."""
        assert task.get_sleep_seconds() == 3600.0


class TestDailyExplorationWorkflow:
    """Tests for DailyExplorationWorkflow execution in isolation.

    The workflow is designed to be scheduled by Temporal only on weekdays,
    so the workflow itself doesn't need weekend-checking logic.
    """

    @pytest.mark.asyncio
    async def test_workflow_executes_successfully(self):
        """Test workflow executes activity successfully.

        The schedule ensures this only runs on weekdays, so the workflow
        always executes the activity when invoked.
        """
        async with await WorkflowEnvironment.start_time_skipping(
            data_converter=pydantic_data_converter
        ) as env:
            task_queue = "test-daily-exploration"

            workflow_runner = SandboxedWorkflowRunner(
                restrictions=SandboxRestrictions.default.with_passthrough_modules("csbot")
            )

            # Set up mock bot provider for activity
            mock_bot = Mock()
            mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")

            mock_bot_provider = Mock()
            mock_bot_provider.fetch_bot = AsyncMock(return_value=mock_bot)

            # Create activity instance with mock bot provider
            activity = DailyExplorationActivity(mock_bot_provider)

            async with Worker(
                env.client,
                task_queue=task_queue,
                workflows=[DailyExplorationWorkflow],
                activities=[activity.send_daily_exploration_activity],
                workflow_runner=workflow_runner,
            ):
                # Mock send_daily_exploration at the module where it's imported
                with patch(
                    "csbot.temporal.daily_exploration.activity.send_daily_exploration"
                ) as mock_send:
                    mock_send.return_value = AsyncMock()

                    result = await env.client.execute_workflow(
                        DailyExplorationWorkflow.run,
                        DailyExplorationWorkflowInput(
                            bot_id="T123-channel",
                            channel_name="test-channel",
                        ),
                        id="test-workflow-execution",
                        task_queue=task_queue,
                    )

                    # Should always complete successfully since schedule handles weekday filtering
                    # Result is a DailyExplorationSuccess object
                    assert result is not None
                    mock_send.assert_called_once()


class TestDailyExplorationActivity:
    """Tests for send_daily_exploration_activity."""

    @pytest.mark.asyncio
    async def test_activity_bot_not_found(self):
        """Test activity raises error when bot not found."""
        # Set up mock bot provider that raises Exception (bot not found)
        mock_bot_provider = Mock()
        mock_bot_provider.fetch_bot = AsyncMock(
            side_effect=Exception("Bot instance not found for T123-channel")
        )

        activity = DailyExplorationActivity(mock_bot_provider)

        with pytest.raises(Exception, match="Bot instance not found for T123-channel"):
            await activity.send_daily_exploration_activity(
                DailyExplorationInput(bot_id="T123-channel", channel_name="test-channel")
            )

    @pytest.mark.asyncio
    async def test_activity_channel_not_found(self):
        """Test activity returns NO_CHANNEL_FOUND when channel not found."""
        # Set up mock bot provider with a bot that returns None for channel_id
        mock_bot = Mock()
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value=None)

        mock_bot_provider = Mock()
        mock_bot_provider.fetch_bot = AsyncMock(return_value=mock_bot)

        activity = DailyExplorationActivity(mock_bot_provider)

        result = await activity.send_daily_exploration_activity(
            DailyExplorationInput(bot_id="T123-channel", channel_name="test-channel")
        )
        assert (
            isinstance(result, DailyExplorationSuccess)
            and result.status == DailyExplorationStatus.NO_CHANNEL_FOUND
        )

    @pytest.mark.asyncio
    async def test_activity_successful_execution(self):
        """Test activity executes successfully."""
        # Set up mock bot provider with a successful bot
        mock_bot = Mock()
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")

        mock_bot_provider = Mock()
        mock_bot_provider.fetch_bot = AsyncMock(return_value=mock_bot)

        activity = DailyExplorationActivity(mock_bot_provider)

        # Mock send_daily_exploration at the module where it's imported in the activity
        with patch("csbot.temporal.daily_exploration.activity.send_daily_exploration") as mock_send:
            mock_send.return_value = AsyncMock()

            result = await activity.send_daily_exploration_activity(
                DailyExplorationInput(bot_id="T123-channel", channel_name="test-channel")
            )

            # Result should be a DailyExplorationSuccess object
            assert result is not None
            mock_send.assert_called_once_with(mock_bot, "C123456")

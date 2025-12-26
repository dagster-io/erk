"""Tests for DatasetMonitoring Temporal workflow."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from csbot.contextengine.contextstore_protocol import Dataset
from csbot.csbot_client.csbot_profile import ConnectionProfile, ProjectProfile
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
from csbot.temporal.dataset_monitor.activity import (
    DatasetMonitoringActivity,
)
from csbot.temporal.dataset_monitor.workflow import (
    DatasetMonitoringWorkflow,
    DatasetMonitoringWorkflowInput,
)
from csbot.temporal.utils import BotProvider
from tests.factories.context_store_factory import context_store_builder


class ConstantBotProvider(BotProvider):
    """BotProvider that returns a single constant bot for testing."""

    def __init__(self, bot: CompassChannelBaseBotInstance):
        self._bot = bot

    async def fetch_bot(self, bot_key: BotKey) -> CompassChannelBaseBotInstance:
        return self._bot

    def get_config(self):
        from unittest.mock import Mock

        return Mock()


@pytest.mark.asyncio
async def test_dataset_monitoring_workflow_happy_path():
    """Test dataset monitoring workflow processes all datasets successfully."""
    async with await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter
    ) as env:
        task_queue = "test-dataset-monitor"

        workflow_runner = SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("csbot")
        )

        # Create test datasets
        dataset1 = Dataset(table_name="sales", connection="prod_db")
        dataset2 = Dataset(table_name="users", connection="prod_db")

        # Create ContextStore with datasets
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .add_dataset(dataset1)
            .add_dataset(dataset2)
            .build()
        )

        # Create mock bot
        mock_bot = Mock(spec=CompassChannelBaseBotInstance)
        mock_bot.local_context_store = Mock()
        mock_bot.profile = Mock()
        mock_bot.kv_store = Mock()
        mock_bot.agent = Mock()
        mock_bot.github_monitor = Mock()
        mock_bot.profile = ProjectProfile(
            connections={
                "prod_db": ConnectionProfile(
                    url="",
                    additional_sql_dialect=None,
                )
            }
        )

        # Mock bot.load_context_store to return our test context store
        mock_bot.load_context_store = AsyncMock(return_value=context_store)

        # Create ConstantBotProvider
        bot_provider = ConstantBotProvider(mock_bot)

        # Create activities
        from csbot.temporal.shared_activities.context_store_loader import ContextStoreLoaderActivity

        context_store_loader_activity = ContextStoreLoaderActivity(bot_provider)
        dataset_monitoring_activity = DatasetMonitoringActivity(bot_provider)

        # Mock DatasetMonitor.check_and_update_dataset_if_changed
        with patch(
            "csbot.temporal.dataset_monitor.activity.DatasetMonitor.check_and_update_dataset_if_changed"
        ) as mock_check:
            # Return None (no PR created) for both datasets
            mock_check.return_value = None

            async with Worker(
                env.client,
                task_queue=task_queue,
                workflows=[DatasetMonitoringWorkflow],
                activities=[
                    context_store_loader_activity.load_context_store,
                    dataset_monitoring_activity.dataset_monitor_activity,
                ],
                workflow_runner=workflow_runner,
            ):
                result = await env.client.execute_workflow(
                    DatasetMonitoringWorkflow.run,
                    DatasetMonitoringWorkflowInput(bot_id="T123-test-channel"),
                    id="test-dataset-monitor-workflow",
                    task_queue=task_queue,
                )

                # Verify workflow completed successfully
                assert result is not None
                assert result.success is True

                # Verify check_and_update_dataset_if_changed was called for each dataset
                assert mock_check.call_count == 2

                # Verify it was called with correct dataset arguments
                calls = mock_check.call_args_list
                dataset_args = [call[0][0] for call in calls]
                assert dataset1 in dataset_args
                assert dataset2 in dataset_args

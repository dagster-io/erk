"""Tests for DatasetSyncWorkflow and activities."""

from contextlib import AsyncExitStack, ExitStack
from unittest.mock import AsyncMock, Mock, patch

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from csbot.csbot_client.csbot_profile import ProjectProfile
from csbot.slackbot.bot_server.bot_reconciler import CompassBotReconciler
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.temporal.dataset_sync.activity import (
    CreateBranchInput,
    DatasetSyncActivities,
    LogAnalyticsInput,
    ProcessDatasetInput,
    SendCompletionNotificationInput,
    SendNotificationInput,
    SendSlackConnectInviteInput,
)
from csbot.temporal.dataset_sync.workflow import (
    DatasetSyncWorkflow,
    DatasetSyncWorkflowInput,
    DatasetSyncWorkflowResult,
)
from csbot.temporal.utils import BotReconcilerBotProvider
from tests.factories.context_store_factory import context_store_builder


@pytest.fixture
def mock_bot_setup():
    """Create a fully configured mock bot and reconciler."""
    mock_bot_reconciler = Mock(spec=CompassBotReconciler)
    mock_bot = Mock()
    mock_bot.governance_alerts_channel = "governance-alerts"
    mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")
    mock_bot.client = Mock()
    mock_bot.client.chat_postMessage = AsyncMock()
    mock_bot.local_context_store.shared_repo.force_refresh = Mock()
    mock_bot.local_context_store.shared_repo.repo_config.github_config = Mock()
    mock_bot.analytics_store = Mock()
    mock_bot.bot_config.organization_id = "org-123"
    mock_bot.bot_config.organization_name = "Test Org"
    mock_bot.key.to_bot_id = Mock(return_value="T123-test-channel")
    mock_bot.key.team_id = "T123"

    # Mock GitHub API client for process_dataset activity

    mock_bot.load_context_store = AsyncMock(return_value=context_store_builder().build())

    mock_bot.profile = ProjectProfile(connections={})
    mock_bot.agent = Mock()

    bot_key = BotKey.from_bot_id("T123-test-channel")
    mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

    return mock_bot_reconciler, mock_bot


class TestDatasetSyncWorkflow:
    """Tests for DatasetSyncWorkflow execution."""

    async def setup_workflow_environment(
        self, mock_bot_reconciler, task_queue: str, stack: AsyncExitStack
    ):
        """Set up workflow environment with worker and activities.

        Args:
            mock_bot_reconciler: Mock bot reconciler instance
            task_queue: Task queue name for the worker
            stack: AsyncExitStack to register context managers with

        Returns tuple of (env, mock_post, mock_analytics).
        """
        env = await stack.enter_async_context(
            await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter)
        )
        workflow_runner = SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("csbot")
        )

        # Create mock temporal client
        mock_temporal_client = Mock()
        mock_workflow_handle = Mock()
        mock_workflow_handle.signal = AsyncMock()
        mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)

        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities_instance = DatasetSyncActivities(bot_provider, mock_temporal_client)

        await stack.enter_async_context(
            Worker(
                env.client,
                task_queue=task_queue,
                workflows=[DatasetSyncWorkflow],
                activities=[
                    activities_instance.create_branch,
                    activities_instance.finalize_pull_request,
                    activities_instance.process_dataset,
                    activities_instance.send_notification_started,
                    activities_instance.send_notification_completed,
                    activities_instance.send_slack_connect_invite,
                    activities_instance.log_analytics,
                ],
                workflow_runner=workflow_runner,
            )
        )

        # Common mocks
        mock_create_merge_pr = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.create_and_merge_pull_request")
        )
        mock_create_merge_pr.return_value = "https://github.com/example/repo/pull/123"

        mock_post = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.SlackstreamMessage.post_message")
        )
        mock_message = Mock()
        mock_message.message_ts = "1234567890.123456"
        mock_post.return_value = mock_message

        # Mock SlackstreamMessage.update for completion notification
        mock_update = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.SlackstreamMessage.update")
        )
        mock_update.return_value = AsyncMock()

        mock_analytics = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.log_analytics_event_unified")
        )
        mock_analytics.return_value = AsyncMock()

        mock_analyze = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.analyze_table_schema")
        )
        mock_analyze.return_value = Mock()

        stack.enter_context(
            patch(
                "csbot.temporal.dataset_sync.activity.update_dataset",
                return_value=context_store_builder().build(),
            )
        )

        stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.get_file_updates", return_value={})
        )

        return env, mock_post, mock_analytics

    @pytest.mark.asyncio
    async def test_workflow_executes_successfully_with_all_datasets(self, mock_bot_setup):
        """Test workflow executes successfully when all datasets process without errors."""
        mock_bot_reconciler, _ = mock_bot_setup

        async with AsyncExitStack() as stack:
            env, mock_post, mock_analytics = await self.setup_workflow_environment(
                mock_bot_reconciler, "test-dataset-sync", stack
            )

            result = await env.client.execute_workflow(
                DatasetSyncWorkflow.run,
                DatasetSyncWorkflowInput(
                    bot_id="T123-test-channel",
                    connection_name="test-connection",
                    table_names=["table1", "table2", "table3"],
                    connection_type="connection",
                    governance_channel_id="C123456",
                ),
                id="test-workflow-success",
                task_queue="test-dataset-sync",
            )

            # Verify result
            assert isinstance(result, DatasetSyncWorkflowResult)
            assert result.pr_url
            assert len(result.processed_datasets) == 3
            assert len(result.failed_datasets) == 0
            assert result.sync_duration_seconds > 0

            # Verify Slack notification was sent
            assert mock_post.call_count >= 1

            # Verify analytics was logged
            assert mock_analytics.call_count >= 1

    @pytest.mark.asyncio
    async def test_workflow_handles_partial_failure(self):
        """Test workflow continues when one dataset fails during parallel processing."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            task_queue = "test-dataset-sync-partial-failure"

            workflow_runner = SandboxedWorkflowRunner(
                restrictions=SandboxRestrictions.default.with_passthrough_modules("csbot")
            )

            context_store = context_store_builder().build()
            mock_bot_reconciler = Mock(spec=CompassBotReconciler)
            mock_bot = Mock()
            mock_bot.governance_alerts_channel = "governance-alerts"
            mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")
            mock_bot.client = Mock()
            mock_bot.client.chat_postMessage = AsyncMock()
            mock_bot.load_context_store = AsyncMock(return_value=context_store)
            mock_bot.analytics_store = Mock()
            mock_bot.bot_config.organization_id = "org-123"
            mock_bot.bot_config.organization_name = "Test Org"
            mock_bot.key.to_bot_id = Mock(return_value="T123-test-channel")
            mock_bot.key.team_id = "T123"

            # Mock GitHub API client for fetching contextstore_project.yaml
            mock_repo = Mock()
            mock_repo.default_branch = "main"

            mock_bot.profile = ProjectProfile(connections={})
            mock_bot.agent = Mock()

            bot_key = BotKey.from_bot_id("T123-test-channel")
            mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

            # Mock temporal client for signaling
            mock_workflow_handle = Mock()
            mock_workflow_handle.signal = AsyncMock()
            mock_temporal_client = Mock()
            mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)
            bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
            activities_instance = DatasetSyncActivities(bot_provider, mock_temporal_client)

            async with Worker(
                env.client,
                task_queue=task_queue,
                workflows=[DatasetSyncWorkflow],
                activities=[
                    activities_instance.create_branch,
                    activities_instance.finalize_pull_request,
                    activities_instance.process_dataset,
                    activities_instance.send_notification_started,
                    activities_instance.send_notification_completed,
                    activities_instance.send_slack_connect_invite,
                    activities_instance.log_analytics,
                ],
                workflow_runner=workflow_runner,
            ):
                with ExitStack() as stack:
                    mock_create_merge_pr = stack.enter_context(
                        patch("csbot.temporal.dataset_sync.activity.create_and_merge_pull_request")
                    )
                    mock_post = stack.enter_context(
                        patch(
                            "csbot.temporal.dataset_sync.activity.SlackstreamMessage.post_message"
                        )
                    )
                    # Mock SlackstreamMessage.update for completion notification
                    mock_update = stack.enter_context(
                        patch("csbot.temporal.dataset_sync.activity.SlackstreamMessage.update")
                    )
                    mock_update.return_value = AsyncMock()

                    mock_error = stack.enter_context(
                        patch("csbot.temporal.dataset_sync.activity.notify_dataset_error")
                    )
                    mock_analytics = stack.enter_context(
                        patch("csbot.temporal.dataset_sync.activity.log_analytics_event_unified")
                    )
                    mock_analyze = stack.enter_context(
                        patch("csbot.temporal.dataset_sync.activity.analyze_table_schema")
                    )
                    stack.enter_context(
                        patch(
                            "csbot.temporal.dataset_sync.activity.get_file_updates", return_value={}
                        )
                    )
                    stack.enter_context(
                        patch("csbot.temporal.dataset_sync.activity.serialize_context_store")
                    )
                    mock_update = stack.enter_context(
                        patch(
                            "csbot.temporal.dataset_sync.activity.update_dataset",
                            return_value=context_store,
                        )
                    )

                    mock_create_merge_pr.return_value = "https://github.com/example/repo/pull/123"
                    mock_message = Mock()
                    mock_message.message_ts = "1234567890.123456"
                    mock_post.return_value = mock_message
                    mock_error.return_value = AsyncMock()
                    mock_analytics.return_value = AsyncMock()

                    # Make table2 fail during schema analysis
                    def analyze_side_effect(logger, profile, dataset):
                        if dataset.table_name == "table2":
                            raise RuntimeError("Schema analysis failed")
                        return Mock()

                    mock_analyze.side_effect = analyze_side_effect
                    mock_update.return_value = None

                    result = await env.client.execute_workflow(
                        DatasetSyncWorkflow.run,
                        DatasetSyncWorkflowInput(
                            bot_id="T123-test-channel",
                            connection_name="test-connection",
                            table_names=["table1", "table2", "table3"],
                            connection_type="connection",
                            governance_channel_id="C123456",
                        ),
                        id="test-workflow-partial-failure",
                        task_queue=task_queue,
                    )

                    # Verify workflow completed with partial success
                    assert isinstance(result, DatasetSyncWorkflowResult)
                    assert result.pr_url
                    assert len(result.processed_datasets) == 2
                    assert len(result.failed_datasets) == 1
                    assert "table2" in result.failed_datasets
                    assert "table1" in result.processed_datasets
                    assert "table3" in result.processed_datasets

                    # Verify error notifications were sent for failed dataset
                    assert mock_error.call_count >= 1

    @pytest.mark.asyncio
    async def test_workflow_handles_empty_table_list(self, mock_bot_setup):
        """Test workflow handles empty table list gracefully."""
        mock_bot_reconciler, _ = mock_bot_setup

        async with AsyncExitStack() as stack:
            env, _, _ = await self.setup_workflow_environment(
                mock_bot_reconciler, "test-dataset-sync-empty", stack
            )

            result = await env.client.execute_workflow(
                DatasetSyncWorkflow.run,
                DatasetSyncWorkflowInput(
                    bot_id="T123-test-channel",
                    connection_name="test-connection",
                    table_names=[],
                    connection_type="connection",
                    governance_channel_id="C123456",
                ),
                id="test-workflow-empty",
                task_queue="test-dataset-sync-empty",
            )

            # Should complete successfully with no datasets
            assert isinstance(result, DatasetSyncWorkflowResult)
            assert len(result.processed_datasets) == 0
            assert len(result.failed_datasets) == 0


class TestDatasetSyncActivities:
    """Tests for individual DatasetSync activities."""

    @pytest.mark.asyncio
    async def test_create_branch_activity(self):
        """Test create_branch activity."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.local_context_store.shared_repo.repo_config.github_config = Mock()
        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        # Mock GitHub API client
        mock_github_client = Mock()
        mock_repo = Mock()
        mock_branch = Mock()
        mock_commit = Mock()
        mock_commit.sha = "abc123"
        mock_branch.commit = mock_commit
        mock_repo.get_branch = Mock(return_value=mock_branch)
        mock_repo.default_branch = "main"
        mock_repo.create_git_ref = Mock()
        mock_github_client.get_repo = Mock(return_value=mock_repo)
        mock_bot.local_context_store.shared_repo.repo_config.github_config.auth_source.get_github_client = Mock(
            return_value=mock_github_client
        )

        result = await activities.create_branch(
            CreateBranchInput(
                bot_id="T123-test-channel",
                connection_name="test-connection",
            )
        )

        assert result.pr_branch.startswith("dataset-sync-test-connection-")
        mock_repo.create_git_ref.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_dataset_activity_success(self):
        """Test process_dataset activity succeeds."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()

        # Mock local_context_store
        mock_bot.local_context_store.update_to_latest = Mock()
        mock_bot.local_context_store.shared_repo.repo_config.github_config = Mock()
        mock_bot.profile = ProjectProfile(connections={})
        mock_bot.agent = Mock()

        # Mock GitHub API client for fetching contextstore_project.yaml
        mock_repo = Mock()
        mock_repo.default_branch = "main"

        context_store = context_store_builder().build()
        mock_bot.load_context_store = AsyncMock(return_value=context_store)

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        # Mock temporal client and workflow handle for signal sending
        mock_workflow_handle = AsyncMock()
        mock_temporal_client = Mock()
        mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with ExitStack() as stack:
            # Mock activity.info() to provide workflow_id
            mock_activity_info = stack.enter_context(
                patch("csbot.temporal.dataset_sync.activity.activity.info")
            )
            mock_info = Mock()
            mock_info.workflow_id = "test-workflow-id"
            mock_activity_info.return_value = mock_info

            mock_analyze = stack.enter_context(
                patch("csbot.temporal.dataset_sync.activity.analyze_table_schema")
            )
            mock_analyze.return_value = Mock()

            stack.enter_context(
                patch(
                    "csbot.temporal.dataset_sync.activity.update_dataset",
                    return_value=context_store,
                )
            )

            stack.enter_context(
                patch("csbot.temporal.dataset_sync.activity.get_file_updates", return_value={})
            )
            stack.enter_context(
                patch("csbot.temporal.dataset_sync.activity.serialize_context_store")
            )

            # Mock workflow handle for signal sending
            mock_workflow_handle = Mock()
            mock_workflow_handle.signal = AsyncMock()
            mock_temporal_client.get_workflow_handle = Mock(return_value=mock_workflow_handle)

            result = await activities.process_dataset(
                ProcessDatasetInput(
                    bot_id="T123-test-channel",
                    connection_name="test-connection",
                    table_name="test-table",
                    pr_branch="dataset-sync-test-connection-123",
                    governance_channel_id="C123456",
                    message_ts="1234567890.123456",
                )
            )

        assert result.success is True
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_send_notification_started(self):
        """Test send_slack_notification with 'started' type."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.governance_alerts_channel = "governance-alerts"
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")
        mock_bot.client = Mock()

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with patch(
            "csbot.temporal.dataset_sync.activity.SlackstreamMessage.post_message"
        ) as mock_post:
            mock_message = Mock()
            mock_message.message_ts = "1234567890.123456"
            mock_post.return_value = mock_message

            result = await activities.send_notification_started(
                SendNotificationInput(
                    bot_id="T123-test-channel",
                    connection_name="test-connection",
                    governance_channel_id="C123456",
                    table_names=["table1", "table2"],
                )
            )

            assert result.message_ts == "1234567890.123456"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_completed(self):
        """Test send_notification_completed activity."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.governance_alerts_channel = "governance-alerts"
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")
        mock_bot.client = Mock()

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with patch("csbot.temporal.dataset_sync.activity.SlackstreamMessage") as mock_message:
            mock_message_instance = Mock()
            mock_message_instance.update = AsyncMock()
            mock_message.return_value = mock_message_instance

            result = await activities.send_notification_completed(
                SendCompletionNotificationInput(
                    bot_id="T123-test-channel",
                    connection_name="test-connection",
                    governance_channel_id="C123456",
                    message_ts="1234567890.123456",
                    pr_url="https://github.com/example/repo/pull/123",
                    processed_datasets=["table1", "table2"],
                    failed_datasets=[],
                )
            )

            assert result.message_ts == "1234567890.123456"
            mock_message_instance.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_analytics_activity_success(self):
        """Test log_analytics activity with successful sync."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.analytics_store = Mock()
        mock_bot.bot_config.organization_id = "org-123"
        mock_bot.bot_config.organization_name = "Test Org"
        mock_bot.key.to_bot_id = Mock(return_value="T123-test-channel")
        mock_bot.key.team_id = "T123"

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with patch("csbot.temporal.dataset_sync.activity.log_analytics_event_unified") as mock_log:
            mock_log.return_value = AsyncMock()

            result = await activities.log_analytics(
                LogAnalyticsInput(
                    bot_id="T123-test-channel",
                    connection_name="test-connection",
                    connection_type="connection",
                    table_count=3,
                    pr_url="https://github.com/example/repo/pull/123",
                    sync_duration_seconds=45.5,
                    processed_datasets=["table1", "table2", "table3"],
                    failed_datasets=[],
                    governance_channel_id="C123456",
                )
            )

            assert result.success is True
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_activity_bot_not_found(self):
        """Test activities raise error when bot not found."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot_reconciler.get_active_bots = Mock(return_value={})

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with pytest.raises(Exception, match="Bot instance not found"):
            await activities.create_branch(
                CreateBranchInput(
                    bot_id="T123-nonexistent",
                    connection_name="test",
                )
            )

    @pytest.mark.asyncio
    async def test_send_slack_connect_invite_with_pending_user(self):
        """Test send_slack_connect_invite activity with pending user ID."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.key.channel_name = "test-channel"
        mock_bot.key.team_id = "T123"
        mock_bot.key.to_bot_id = Mock(return_value="T123-test-channel")
        mock_bot.kv_store = AsyncMock()
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C456QA")
        mock_bot.kv_store.get = AsyncMock(
            side_effect=["U789USER", None, None]
        )  # user_id, email, metadata
        mock_bot.kv_store.delete = AsyncMock()
        mock_bot.kv_store.set = AsyncMock()
        mock_bot.client = AsyncMock()
        mock_bot.pregenerate_and_store_welcome_message = AsyncMock()
        mock_bot.analytics_store = Mock()
        mock_bot.analytics_store.log_analytics_event = AsyncMock()
        mock_bot.analytics_store.log_analytics_event_with_enriched_user = AsyncMock()
        mock_bot.bot_config.organization_id = "org-123"
        mock_bot.bot_config.organization_name = "Test Org"
        mock_bot.local_context_store.shared_repo.force_refresh = Mock()

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        mock_config = Mock()
        mock_config.compass_dev_tools_bot_token = Mock()
        mock_config.compass_dev_tools_bot_token.get_secret_value.return_value = "test-token"
        mock_bot_reconciler.config = mock_config

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with ExitStack() as stack:
            mock_send_invite = stack.enter_context(
                patch("csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel")
            )
            mock_send_invite.return_value = [{"success": True, "invite": {"id": "I123"}}]

            mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
            mock_to_thread.return_value = None

            result = await activities.send_slack_connect_invite(
                SendSlackConnectInviteInput(
                    bot_id="T123-test-channel",
                    governance_channel_id="C123GOV",
                )
            )

            # Verify result
            assert result.success is True
            assert result.invited_users == ["U789USER"]

            # Verify pending user was retrieved
            mock_bot.kv_store.get.assert_any_call("pending_invites", "user_ids")

            # Verify Slack Connect invite was sent
            mock_send_invite.assert_called_once()

            # Verify pending user was deleted AFTER successful send
            mock_bot.kv_store.delete.assert_any_call("pending_invites", "user_ids")

            # Verify analytics was logged (via bot.analytics_store)
            assert mock_bot.analytics_store.log_analytics_event_with_enriched_user.await_count == 1

            # Verify invite tracking was set
            mock_bot.kv_store.set.assert_called_once_with(
                "invite_tracking", "slack_connect_invite_sent_test-channel", "true"
            )

            # Verify force refresh was called
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_slack_connect_invite_with_no_pending_invites(self):
        """Test send_slack_connect_invite activity with no pending invites (subsequent sync)."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.key.channel_name = "test-channel"
        mock_bot.kv_store = AsyncMock()
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C456QA")
        mock_bot.kv_store.get = AsyncMock(return_value=None)  # No pending invites

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})
        mock_bot_reconciler.config = Mock()

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with patch("csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel") as mock_send:
            result = await activities.send_slack_connect_invite(
                SendSlackConnectInviteInput(
                    bot_id="T123-test-channel",
                    governance_channel_id="C123GOV",
                )
            )

            # Verify result - success but no invites sent
            assert result.success is True
            assert result.invited_users == []

            # Verify Slack Connect invite was NOT called
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_slack_connect_invite_with_pending_email(self):
        """Test send_slack_connect_invite activity with pending email (onboarding flow)."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.key.channel_name = "test-channel"
        mock_bot.key.team_id = "T123"
        mock_bot.key.to_bot_id = Mock(return_value="T123-test-channel")
        mock_bot.kv_store = AsyncMock()
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C456QA")
        mock_bot.kv_store.get = AsyncMock(
            side_effect=[None, "user@example.com", None]
        )  # no user_id, email, no metadata
        mock_bot.kv_store.delete = AsyncMock()
        mock_bot.kv_store.set = AsyncMock()
        mock_bot.client = AsyncMock()
        mock_bot.pregenerate_and_store_welcome_message = AsyncMock()
        mock_bot.bot_config.organization_id = "org-123"
        mock_bot.local_context_store.shared_repo.force_refresh = Mock()

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})

        mock_config = Mock()
        mock_config.compass_dev_tools_bot_token = Mock()
        mock_config.compass_dev_tools_bot_token.get_secret_value.return_value = "test-token"
        mock_bot_reconciler.config = mock_config

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with ExitStack() as stack:
            mock_create_connect = stack.enter_context(
                patch("csbot.slackbot.slack_utils.create_slack_connect_channel")
            )
            mock_create_connect.return_value = {"success": True}

            mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
            mock_to_thread.return_value = None

            result = await activities.send_slack_connect_invite(
                SendSlackConnectInviteInput(
                    bot_id="T123-test-channel",
                    governance_channel_id="C123GOV",
                )
            )

            # Verify result
            assert result.success is True
            assert result.invited_users == []  # Email invites don't return user IDs

            # Verify email invite was sent
            mock_create_connect.assert_called_once()

            # Verify pending email was deleted AFTER successful send
            mock_bot.kv_store.delete.assert_any_call("pending_invites", "emails")

    @pytest.mark.asyncio
    async def test_send_slack_connect_invite_handles_failure(self):
        """Test send_slack_connect_invite activity handles invite failure gracefully."""
        mock_bot_reconciler = Mock(spec=CompassBotReconciler)
        mock_bot = Mock()
        mock_bot.key.channel_name = "test-channel"
        mock_bot.kv_store = AsyncMock()
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C456QA")
        mock_bot.kv_store.get = AsyncMock(side_effect=["U789USER", None, None])
        mock_bot.kv_store.delete = AsyncMock()
        mock_bot.pregenerate_and_store_welcome_message = AsyncMock()

        bot_key = BotKey.from_bot_id("T123-test-channel")
        mock_bot_reconciler.get_active_bots = Mock(return_value={bot_key: mock_bot})
        mock_bot_reconciler.config = Mock()

        mock_temporal_client = Mock()
        bot_provider = BotReconcilerBotProvider(mock_bot_reconciler)
        activities = DatasetSyncActivities(bot_provider, mock_temporal_client)

        with patch("csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel") as mock_send:
            # Simulate invite failure
            mock_send.return_value = [{"success": False, "error": "api_error"}]

            result = await activities.send_slack_connect_invite(
                SendSlackConnectInviteInput(
                    bot_id="T123-test-channel",
                    governance_channel_id="C123GOV",
                )
            )

            # Verify result reflects failure
            assert result.success is False
            assert result.invited_users == []

            # Verify pending invite was NOT deleted on failure (allows retry)
            mock_bot.kv_store.delete.assert_not_called()

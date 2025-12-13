"""Unit tests for dataset sync functionality including Slack connect invites after first database sync."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csbot.slackbot.webapp.add_connections.dataset_sync import (
    send_pending_slack_connect_invite,
    sync_datasets_after_connection,
)


class TestDatasetSync:
    """Test dataset sync functionality."""

    @pytest.fixture
    def mock_bot_server(self):
        """Create a mock bot server."""
        mock_bot_server = MagicMock()
        mock_bot_server.config = MagicMock()
        mock_bot_server.config.compass_dev_tools_bot_token = MagicMock()
        mock_bot_server.config.compass_dev_tools_bot_token.get_secret_value.return_value = (
            "test_token_12345"
        )
        mock_bot_server.config.dagster_admins_to_invite = ["admin1@dagster.io", "admin2@dagster.io"]

        # Mock Temporal client for workflow execution
        mock_bot_server.temporal_client = AsyncMock()
        mock_bot_server.temporal_client.start_workflow = AsyncMock()

        return mock_bot_server

    @pytest.fixture
    def mock_bot_instance(self):
        """Create a mock bot instance."""
        mock_bot = MagicMock()
        mock_bot.key.channel_name = "test-company-compass"
        mock_bot.key.to_bot_id = MagicMock(return_value="mock-bot-id")
        mock_bot.key.team_id = "T123TEST"
        mock_bot.governance_alerts_channel = "test-company-compass-governance"
        mock_bot.client = AsyncMock()
        mock_bot.kv_store = AsyncMock()
        mock_bot.kv_store.get_channel_id = AsyncMock()
        mock_bot.kv_store.set = AsyncMock()
        mock_bot.profile = MagicMock()
        mock_bot.bot_config = MagicMock()
        mock_bot.bot_config.organization_id = "org_12345"
        mock_bot.bot_config.organization_name = "Test Organization"
        mock_bot.bot_config.channel_name = "test-company-compass"

        # Mock the analytics store with async methods
        mock_bot.analytics_store = MagicMock()
        mock_bot.analytics_store.log_analytics_event = AsyncMock()
        mock_bot.analytics_store.log_analytics_event_with_enriched_user = AsyncMock()

        return mock_bot

    @pytest.mark.asyncio
    async def test_sync_datasets_after_connection_calls_slack_invite_on_first_sync(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test that sync_datasets_after_connection calls Slack connect invite and force refresh for first dataset sync."""
        # Mock the bot server's bots dict
        bot_key = "test_bot_key"
        mock_bot_server.bots = {bot_key: mock_bot_instance}

        # Mock sleep and channel IDs
        mock_bot_instance.kv_store.get_channel_id.side_effect = [
            "C123GOVERNANCE",  # governance channel ID
            "C456MAIN",  # main channel ID
            "C123GOVERNANCE",  # governance channel ID (second call)
        ]

        # Mock local context store and its force_refresh method
        mock_bot_instance.local_context_store = MagicMock()
        mock_bot_instance.local_context_store.shared_repo = MagicMock()
        mock_bot_instance.local_context_store.shared_repo.force_refresh = MagicMock()

        # Mock logger
        mock_logger = MagicMock()

        with patch(
            "csbot.slackbot.webapp.add_connections.dataset_sync.sleep_until_ready"
        ) as mock_sleep:
            # Configure mocks
            mock_sleep.return_value = None
            # Note: Slack Connect invite logic is now handled inside the Temporal workflow
            # so we don't need to mock _is_first_dataset_sync or send_pending_slack_connect_invite

            # Call the function
            await sync_datasets_after_connection(
                bot_key=bot_key,
                bot_server=mock_bot_server,
                connection_name="test_connection",
                table_names=["schema.table1", "schema.table2"],
                logger=mock_logger,
                connection_type="database",
            )

            # Verify sleep was called
            mock_sleep.assert_called_once()

            # Verify Temporal workflow was started (fire-and-forget)
            mock_bot_server.temporal_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_datasets_after_connection_skips_slack_invite_on_subsequent_syncs(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test that sync_datasets_after_connection skips Slack connect invite and force refresh for subsequent syncs."""
        # Mock the bot server's bots dict
        bot_key = "test_bot_key"
        mock_bot_server.bots = {bot_key: mock_bot_instance}

        # Mock sleep and channel IDs
        mock_bot_instance.kv_store.get_channel_id.return_value = "C123GOVERNANCE"

        # Mock local context store - should not be called in subsequent syncs
        mock_bot_instance.local_context_store = MagicMock()
        mock_bot_instance.local_context_store.shared_repo = MagicMock()
        mock_bot_instance.local_context_store.shared_repo.force_refresh = MagicMock()

        # Mock logger
        mock_logger = MagicMock()

        with patch(
            "csbot.slackbot.webapp.add_connections.dataset_sync.sleep_until_ready"
        ) as mock_sleep:
            # Configure mocks
            mock_sleep.return_value = None
            # Note: Slack Connect invite logic is now handled inside the Temporal workflow
            # This test is now redundant since the workflow decides whether to send invites

            # Call the function
            await sync_datasets_after_connection(
                bot_key=bot_key,
                bot_server=mock_bot_server,
                connection_name="test_connection",
                table_names=["schema.table1"],
                logger=mock_logger,
                connection_type="database",
            )

            # Verify Temporal workflow was started (fire-and-forget)
            mock_bot_server.temporal_client.start_workflow.assert_called_once()
            mock_bot_instance.logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_datasets_after_connection_handles_errors_gracefully(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test that sync_datasets_after_connection handles errors gracefully and posts error notifications."""
        # Mock the bot server's bots dict
        bot_key = "test_bot_key"
        mock_bot_server.bots = {bot_key: mock_bot_instance}

        # Mock sleep and channel IDs
        mock_bot_instance.kv_store.get_channel_id.return_value = "C123GOVERNANCE"

        # Mock logger
        mock_logger = MagicMock()

        with (
            patch(
                "csbot.slackbot.webapp.add_connections.dataset_sync.sleep_until_ready"
            ) as mock_sleep,
        ):
            # Configure mocks to raise an exception in temporal workflow
            mock_sleep.return_value = None
            mock_bot_server.temporal_client.start_workflow.side_effect = Exception(
                "Workflow execution failed"
            )

            # Call the function - should not raise
            await sync_datasets_after_connection(
                bot_key=bot_key,
                bot_server=mock_bot_server,
                connection_name="test_connection",
                table_names=["schema.table1"],
                logger=mock_logger,
                connection_type="database",
            )

            # Verify error was logged
            mock_logger.error.assert_called_with(
                "Error syncing datasets after connection setup: Workflow execution failed",
                exc_info=True,
            )


class TestSendMainChannelSlackConnectInvite:
    """Test send_pending_slack_connect_invite function."""

    @pytest.fixture
    def mock_bot_server(self):
        """Create a mock bot server."""
        mock_bot_server = MagicMock()
        mock_bot_server.config = MagicMock()
        mock_bot_server.config.compass_dev_tools_bot_token = MagicMock()
        mock_bot_server.config.compass_dev_tools_bot_token.get_secret_value.return_value = (
            "test_org_bot_token"
        )
        mock_bot_server.config.dagster_admins_to_invite = ["admin1@dagster.io", "admin2@dagster.io"]
        return mock_bot_server

    @pytest.fixture
    def mock_bot_instance(self):
        """Create a mock bot instance."""
        mock_bot = MagicMock()
        mock_bot.key.channel_name = "test-company-compass"
        mock_bot.key.team_id = "T123TEAM"
        mock_bot.key.to_bot_id.return_value = "bot_12345"
        mock_bot.governance_alerts_channel = "test-company-compass-governance"
        mock_bot.client = AsyncMock()
        mock_bot.kv_store = AsyncMock()
        mock_bot.analytics_store = AsyncMock()
        mock_bot.bot_config.organization_id = "org_12345"
        mock_bot.pregenerate_and_store_welcome_message = AsyncMock()
        return mock_bot

    @pytest.mark.asyncio
    async def testsend_pending_slack_connect_invite_success(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test successful Slack connect invite sending with pending user ID."""
        # Mock logger
        mock_logger = MagicMock()

        # Mock channel IDs
        mock_bot_instance.kv_store.get_channel_id.side_effect = [
            "C456MAIN",  # main channel ID
            "C123GOVERNANCE",  # governance channel ID
        ]

        # Mock pending invite check - return a pending user ID
        mock_bot_instance.kv_store.get.side_effect = [
            "U1234USER",  # pending user_ids
            None,  # pending emails
            None,  # message_stream_metadata
        ]
        mock_bot_instance.kv_store.delete = AsyncMock()

        with patch(
            "csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel",
            new_callable=AsyncMock,
        ) as mock_send_invite:
            # Configure mocks
            mock_send_invite.return_value = [
                {"success": True, "invite": {"id": "I12345"}},
            ]

            # Call the function
            await send_pending_slack_connect_invite(
                bot_server=mock_bot_server,
                bot=mock_bot_instance,
                logger=mock_logger,
            )

            # Verify channel IDs were retrieved
            assert mock_bot_instance.kv_store.get_channel_id.call_count == 2
            mock_bot_instance.kv_store.get_channel_id.assert_any_call("test-company-compass")
            mock_bot_instance.kv_store.get_channel_id.assert_any_call(
                "test-company-compass-governance"
            )

            # Verify pending invites were checked (3 calls: user_ids, emails, message_stream_metadata)
            assert mock_bot_instance.kv_store.get.call_count == 3
            mock_bot_instance.kv_store.get.assert_any_call("pending_invites", "user_ids")
            mock_bot_instance.kv_store.get.assert_any_call("pending_invites", "emails")
            mock_bot_instance.kv_store.get.assert_any_call(
                "pending_invites", "message_stream_metadata"
            )

            # Verify Slack connect invite was sent once with the pending user ID
            mock_send_invite.assert_called_once_with(
                channel_id="C456MAIN",
                user_ids=["U1234USER"],
                bot_server_config=mock_bot_server.config,
                logger=mock_logger,
                channel_name="test-company-compass",
            )

            # Verify pending user_id was deleted from kvstore AFTER successful send
            mock_bot_instance.kv_store.delete.assert_called_once_with("pending_invites", "user_ids")

            # Verify KV store was called to mark invite as sent for this channel
            mock_bot_instance.kv_store.set.assert_called_once_with(
                "invite_tracking", "slack_connect_invite_sent_test-company-compass", "true"
            )
            mock_bot_instance.client.chat_postMessage.assert_called_once_with(
                channel="C123GOVERNANCE",
                text="Your new Compass channel <#C456MAIN> is ready!",
            )

            # Verify success was logged (check the final summary message)
            assert any(
                "Successfully sent Slack Connect invite to Q&A channel" in str(call)
                for call in mock_logger.info.call_args_list
            )

    @pytest.mark.asyncio
    async def testsend_pending_slack_connect_invite_no_main_channel(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test handling when main channel ID cannot be found."""
        # Mock logger
        mock_logger = MagicMock()

        # Mock main channel ID as None (not found)
        mock_bot_instance.kv_store.get_channel_id.return_value = None

        # Call the function
        await send_pending_slack_connect_invite(
            bot_server=mock_bot_server,
            bot=mock_bot_instance,
            logger=mock_logger,
        )

        # Verify error was logged and function returned early
        mock_logger.error.assert_called_with(
            "Error sending Q&A channel Slack Connect invite: Could not find Q&A channel ID for: test-company-compass",
            exc_info=True,
        )

    @pytest.mark.asyncio
    async def testsend_pending_slack_connect_invite_no_bot_token(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test handling when send_slack_connect_invite_to_channel fails due to missing token."""
        # Mock logger
        mock_logger = MagicMock()

        # Mock channel IDs as found
        mock_bot_instance.kv_store.get_channel_id.side_effect = [
            "C456MAIN",  # main channel ID
            "C123GOVERNANCE",  # governance channel ID
        ]

        # Mock pending invite check - return a pending user ID
        mock_bot_instance.kv_store.get.side_effect = [
            "U1234USER1",  # pending user_ids
            None,  # pending emails
            None,  # message_stream_metadata
        ]
        mock_bot_instance.kv_store.delete = AsyncMock()

        with patch(
            "csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel",
            new_callable=AsyncMock,
        ) as mock_send_invite:
            # Simulate failure (no token or other error)
            mock_send_invite.return_value = [{"success": False, "error": "No bot token"}]

            # Call the function
            await send_pending_slack_connect_invite(
                bot_server=mock_bot_server,
                bot=mock_bot_instance,
                logger=mock_logger,
            )

            # Verify error was logged
            mock_logger.error.assert_called_with(
                "Failed to create Slack Connect invite for Q&A channel: [{'success': False, 'error': 'No bot token'}]"
            )

            # Verify pending invite was NOT deleted on failure (allows retry)
            mock_bot_instance.kv_store.delete.assert_not_called()

    @pytest.mark.asyncio
    async def testsend_pending_slack_connect_invite_create_connect_failure(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test handling when send_slack_connect_invite_to_channel fails."""
        # Mock logger
        mock_logger = MagicMock()

        # Mock channel IDs
        mock_bot_instance.kv_store.get_channel_id.side_effect = [
            "C456MAIN",  # main channel ID
            "C123GOVERNANCE",  # governance channel ID
        ]

        # Mock pending invite check - return a pending user ID
        mock_bot_instance.kv_store.get.side_effect = [
            "U1234USER1",  # pending user_ids
            None,  # pending emails
            None,  # message_stream_metadata
        ]
        mock_bot_instance.kv_store.delete = AsyncMock()

        with patch(
            "csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel",
            new_callable=AsyncMock,
        ) as mock_send_invite:
            # Configure mocks
            mock_send_invite.return_value = [{"success": False, "error": "api_error"}]

            # Call the function
            await send_pending_slack_connect_invite(
                bot_server=mock_bot_server,
                bot=mock_bot_instance,
                logger=mock_logger,
            )

            # Verify error was logged
            mock_logger.error.assert_called_with(
                "Failed to create Slack Connect invite for Q&A channel: [{'success': False, 'error': 'api_error'}]"
            )

            # Verify no success message was posted
            mock_bot_instance.client.chat_postMessage.assert_not_called()

            # Verify pending invite was NOT deleted on failure (allows retry)
            mock_bot_instance.kv_store.delete.assert_not_called()

    @pytest.mark.asyncio
    async def testsend_pending_slack_connect_invite_exception_handling(
        self, mock_bot_server, mock_bot_instance
    ):
        """Test exception handling in send_pending_slack_connect_invite."""
        # Mock logger
        mock_logger = MagicMock()

        # Mock channel IDs to raise exception
        mock_bot_instance.kv_store.get_channel_id.side_effect = Exception("Channel lookup failed")

        # Call the function - should not raise
        await send_pending_slack_connect_invite(
            bot_server=mock_bot_server,
            bot=mock_bot_instance,
            logger=mock_logger,
        )

        # Verify error was logged with exception info
        mock_logger.error.assert_called_with(
            "Error sending Q&A channel Slack Connect invite: Channel lookup failed", exc_info=True
        )

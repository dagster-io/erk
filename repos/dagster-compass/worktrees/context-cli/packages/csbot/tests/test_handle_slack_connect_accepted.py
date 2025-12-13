"""Test cases for handle_slack_connect_accepted functionality."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from pydantic import SecretStr

from csbot.slackbot.channel_bot.bot import BotTypeQA, CompassChannelQANormalBotInstance
from csbot.slackbot.issue_creator.github import GithubIssueCreator
from csbot.slackbot.slackbot_core import AnthropicConfig
from csbot.slackbot.storage.onboarding_state import BotInstanceType


class TestHandleSlackConnectAccepted(unittest.TestCase):
    """Test cases for handle_slack_connect_accepted functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock all dependencies
        self.mock_key = Mock()
        self.mock_key.to_bot_id.return_value = "test_bot_id"

        self.mock_logger = Mock()
        self.mock_client = AsyncMock()
        self.mock_kv_store = AsyncMock()
        self.mock_analytics_store = AsyncMock()
        self.mock_bot_config = Mock()
        self.mock_bot_config.organization_id = 123
        self.mock_bot_config.organization_type = BotInstanceType.STANDARD
        self.mock_bot_config.is_prospector = False

        # Mock bot_server and config
        self.mock_bot_server = Mock()
        self.mock_bot_server.config = Mock()
        self.mock_bot_server.config.compass_dev_tools_bot_token = Mock()
        self.mock_bot_server.config.compass_dev_tools_bot_token.get_secret_value.return_value = (
            "admin_token_12345"
        )

        # Create mock ai_config
        mock_ai_config = AnthropicConfig(
            provider="anthropic",
            api_key=SecretStr("test_api_key"),
            model="claude-sonnet-4-20250514",
        )

        # Create bot instance with minimal mocking
        self.bot = CompassChannelQANormalBotInstance(
            key=self.mock_key,
            logger=self.mock_logger,
            github_config=Mock(),
            local_context_store=Mock(),
            client=self.mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=mock_ai_config,
            kv_store=self.mock_kv_store,
            governance_alerts_channel="governance",
            analytics_store=self.mock_analytics_store,
            profile=Mock(),
            csbot_client=Mock(),
            data_request_github_creds=Mock(),
            slackbot_github_monitor=Mock(),
            scaffold_branch_enabled=False,
            bot_config=self.mock_bot_config,
            bot_type=BotTypeQA(),
            server_config=self.mock_bot_server.config,
            storage=Mock(),
            issue_creator=GithubIssueCreator(Mock()),
        )

    def test_successful_slack_connect_accepted(self):
        """Test successful handling of shared_channel_invite_accepted event."""

        async def run_test():
            # Mock event payload based on actual Slack documentation
            event = {
                "channel": {"id": "C12345CHANNEL"},
                "accepting_user": {"team_id": "T12345TEAM"},
            }

            # Mock successful set_external_invite_permissions response
            with patch(
                "csbot.slackbot.channel_bot.bot.set_external_invite_permissions"
            ) as mock_set_perms:
                mock_set_perms.return_value = {
                    "success": True,
                    "channel": "C12345CHANNEL",
                    "target_team": "T12345TEAM",
                    "action": "upgrade",
                }

                # Call the method
                await self.bot.handle_slack_connect_accepted(event)

                # Verify set_external_invite_permissions was called correctly
                mock_set_perms.assert_called_once_with(
                    admin_token="admin_token_12345",
                    channel="C12345CHANNEL",
                    target_team="T12345TEAM",
                    action="upgrade",
                )

                # Verify success logging
                self.mock_logger.info.assert_any_call(
                    "SLACK_CONNECT_ACCEPTED: {'channel': {'id': 'C12345CHANNEL'}, 'accepting_user': {'team_id': 'T12345TEAM'}}"
                )
                self.mock_logger.info.assert_any_call(
                    "Successfully set external invite permissions for channel C12345CHANNEL after Slack Connect acceptance"
                )

        asyncio.run(run_test())

    def test_set_permissions_api_failure(self):
        """Test handling when set_external_invite_permissions API call fails."""

        async def run_test():
            # Mock event payload
            event = {
                "channel": {"id": "C12345CHANNEL"},
                "accepting_user": {"team_id": "T12345TEAM"},
            }

            # Mock failed set_external_invite_permissions response
            with patch(
                "csbot.slackbot.channel_bot.bot.set_external_invite_permissions"
            ) as mock_set_perms:
                mock_set_perms.return_value = {"success": False, "error": "channel_not_found"}

                # Call the method
                await self.bot.handle_slack_connect_accepted(event)

                # Verify set_external_invite_permissions was called
                mock_set_perms.assert_called_once_with(
                    admin_token="admin_token_12345",
                    channel="C12345CHANNEL",
                    target_team="T12345TEAM",
                    action="upgrade",
                )

                # Verify error logging
                self.mock_logger.error.assert_called_once()
                error_call = self.mock_logger.error.call_args[0][0]
                self.assertIn(
                    "Failed to set external invite permissions for channel C12345CHANNEL",
                    error_call,
                )
                self.assertIn("{'success': False, 'error': 'channel_not_found'}", error_call)

        asyncio.run(run_test())

    def test_exception_handling(self):
        """Test handling when an exception occurs during processing."""

        async def run_test():
            # Mock event payload
            event = {
                "channel": {"id": "C12345CHANNEL"},
                "accepting_user": {"team_id": "T12345TEAM"},
            }

            # Mock exception in set_external_invite_permissions
            with patch(
                "csbot.slackbot.channel_bot.bot.set_external_invite_permissions"
            ) as mock_set_perms:
                mock_set_perms.side_effect = Exception("Network error")

                # Call the method
                await self.bot.handle_slack_connect_accepted(event)

                # Verify exception logging
                self.mock_logger.error.assert_called_once()
                error_call = self.mock_logger.error.call_args[0][0]
                self.assertIn(
                    "Error setting external invite permissions after Slack Connect acceptance",
                    error_call,
                )
                self.assertIn("Network error", error_call)

                # Verify exc_info was passed
                self.assertTrue(self.mock_logger.error.call_args[1]["exc_info"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()

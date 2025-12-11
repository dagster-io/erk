"""Integration tests for prospector bot initialization with read-only context engine."""

import asyncio
from unittest.mock import AsyncMock, Mock

from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig, OrganizationConfig
from csbot.slackbot.storage.onboarding_state import BotInstanceType


class TestProspectorBotInitialization:
    """Test that prospector bots are correctly initialized with read-only context engines."""

    def test_bot_config_defaults_to_standard_organization(self):
        """Test that bot config defaults to standard organization type when not specified."""
        config = CompassBotSingleChannelConfig(
            channel_name="test-channel",
            bot_email="bot@example.com",
            team_id="T123",
            connections={},
            governance_alerts_channel="governance",
            organization=OrganizationConfig(
                organization_id=123,
                organization_name="Test Org",
                contextstore_github_repo="test/repo",
            ),
            # Note: instance_type not specified
        )

        # Should default to "standard"
        assert config.instance_type == BotInstanceType.STANDARD
        assert config.is_prospector is False

    def test_prospector_bot_blocks_insight_command(self):
        """Test that !insight command is blocked in prospector mode."""
        from csbot.csbot_client.csbot_profile import ConnectionProfile
        from csbot.slackbot.channel_bot.bot import CompassChannelQANormalBotInstance
        from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME

        # Create prospector config with data_documentation_repos to enable prospector mode
        prospector_config = CompassBotSingleChannelConfig(
            channel_name="prospector-channel",
            bot_email="bot@example.com",
            team_id="T123",
            connections={
                PROSPECTOR_CONNECTION_NAME: ConnectionProfile(
                    url="bigquery://prospector", additional_sql_dialect=None
                )
            },
            governance_alerts_channel="governance",
            organization=OrganizationConfig(
                organization_id=123,
                organization_name="Test Prospector Org",
                contextstore_github_repo="test/repo",
            ),
            instance_type=BotInstanceType.STANDARD,
            data_documentation_repos={"compass/prospector-data-docs"},
        )

        # Create mock for _handle_on_demand_daily_exploration
        mock_handle_daily_exploration = AsyncMock()

        # Create minimal bot instance
        bot = Mock(spec=CompassChannelQANormalBotInstance)
        bot.bot_config = prospector_config
        bot._handle_on_demand_daily_exploration = mock_handle_daily_exploration
        bot.cron_manager = Mock()
        bot.logger = Mock()

        # Mock get_bot_user_id
        async def mock_get_bot_user_id():
            return "U_BOT123"

        bot.get_bot_user_id = mock_get_bot_user_id

        # Import and execute the actual handle_app_mention logic
        from csbot.slackbot.channel_bot.bot import CompassChannelQANormalBotInstance

        # Call the real handle_app_mention method on our mock
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> !insight",
            "ts": "1234567890.123456",
            "channel": "C_CHANNEL123",
            "event_ts": "1234567890.123456",
        }

        # Execute handle_app_mention using the real implementation
        mock_bot_server = Mock()
        asyncio.run(
            CompassChannelQANormalBotInstance.handle_app_mention(bot, mock_bot_server, event)
        )

        # Verify that _handle_on_demand_daily_exploration was NOT called
        # In prospector mode, the command should be blocked before reaching that method
        mock_handle_daily_exploration.assert_not_called()

    def test_prospector_bot_blocks_cron_command(self):
        """Test that !cron command is blocked in prospector mode."""
        from csbot.csbot_client.csbot_profile import ConnectionProfile
        from csbot.slackbot.channel_bot.bot import CompassChannelQANormalBotInstance
        from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME

        # Create prospector config with data_documentation_repos to enable prospector mode
        prospector_config = CompassBotSingleChannelConfig(
            channel_name="prospector-channel",
            bot_email="bot@example.com",
            team_id="T123",
            connections={
                PROSPECTOR_CONNECTION_NAME: ConnectionProfile(
                    url="bigquery://prospector", additional_sql_dialect=None
                )
            },
            governance_alerts_channel="governance",
            organization=OrganizationConfig(
                organization_id=123,
                organization_name="Test Prospector Org",
                contextstore_github_repo="test/repo",
            ),
            instance_type=BotInstanceType.STANDARD,
            data_documentation_repos={"compass/prospector-data-docs"},
        )

        # Create minimal bot instance mock
        bot = Mock(spec=CompassChannelQANormalBotInstance)
        bot.bot_config = prospector_config
        bot.logger = Mock()

        # Mock cron_manager with handle_cron_command
        mock_cron_manager = Mock()
        mock_cron_manager.handle_cron_command = AsyncMock()
        bot.cron_manager = mock_cron_manager

        # Mock _handle_on_demand_daily_exploration (not used in this test but needed for spec)
        bot._handle_on_demand_daily_exploration = AsyncMock()

        # Mock get_bot_user_id
        async def mock_get_bot_user_id():
            return "U_BOT123"

        bot.get_bot_user_id = mock_get_bot_user_id

        # Create event with !cron command
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> !cron test_job",
            "ts": "1234567890.123456",
            "channel": "C_CHANNEL123",
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention using the real implementation
        mock_bot_server = Mock()
        asyncio.run(
            CompassChannelQANormalBotInstance.handle_app_mention(bot, mock_bot_server, event)
        )

        # Verify that cron_manager.handle_cron_command was NOT called
        mock_cron_manager.handle_cron_command.assert_not_called()

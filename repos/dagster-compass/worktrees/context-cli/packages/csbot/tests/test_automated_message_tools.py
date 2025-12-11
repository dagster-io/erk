"""Tests for automated message tool restrictions."""

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr

from csbot.slackbot.channel_bot.bot import BotTypeQA, CompassChannelQANormalBotInstance
from csbot.slackbot.issue_creator.github import GithubIssueCreator
from csbot.slackbot.slackbot_core import AnthropicConfig
from csbot.slackbot.storage.onboarding_state import BotInstanceType


class TestAutomatedMessageTools:
    """Test that automated messages have restricted tools."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance."""
        # Mock all required dependencies
        mock_key = Mock()
        mock_key.to_bot_id.return_value = "test_bot_id"

        mock_ai_config = AnthropicConfig(
            provider="anthropic",
            api_key=SecretStr("test_api_key"),
            model="claude-sonnet-4-20250514",
        )

        mock_csbot_client = Mock()
        mock_csbot_client.run_sql_query = AsyncMock()
        mock_csbot_client.search_datasets = AsyncMock()
        mock_csbot_client.search_context = AsyncMock()

        mock_cron_manager = Mock()
        mock_cron_manager.get_cron_tools = AsyncMock(
            return_value={
                "add_cron_job": AsyncMock(),
                "remove_cron_job": AsyncMock(),
                "list_cron_jobs": AsyncMock(),
            }
        )

        # Create bot instance
        bot = CompassChannelQANormalBotInstance(
            key=mock_key,
            logger=Mock(),
            github_config=Mock(),
            local_context_store=Mock(),
            client=AsyncMock(),
            bot_background_task_manager=AsyncMock(),
            ai_config=mock_ai_config,
            kv_store=AsyncMock(),
            governance_alerts_channel="governance",
            analytics_store=AsyncMock(),
            profile=Mock(),
            csbot_client=mock_csbot_client,
            data_request_github_creds=Mock(),
            slackbot_github_monitor=Mock(),
            scaffold_branch_enabled=False,
            bot_config=Mock(
                organization_type=BotInstanceType.STANDARD,
                is_prospector=False,
                organization_id=1,
            ),
            bot_type=BotTypeQA(),
            server_config=Mock(),
            storage=AsyncMock(),
            issue_creator=GithubIssueCreator(Mock()),
        )

        # Override cron manager after initialization
        bot.cron_manager = mock_cron_manager

        # Mock contextstore to support cron jobs (standard org)
        mock_csbot_client.contextstore = Mock()
        mock_csbot_client.contextstore.supports_cron_jobs = Mock(return_value=True)
        mock_csbot_client.contextstore.supports_add_context = Mock(return_value=True)

        return bot

    @pytest.mark.asyncio
    async def test_automated_message_has_restricted_tools(self, mock_bot):
        """Test that automated messages only get read-only tools."""
        tools = await mock_bot.get_tools_for_message(
            channel="C123",
            message_ts=None,
            thread_ts="T1234",
            user=None,
            is_automated_message=True,
        )

        # Should only have read-only tools
        expected_tools = {
            "run_sql_query",
            "search_datasets",
            "search_context",
            "render_data_visualization",
            "search_web",
            "attach_csv",
        }
        assert set(tools.keys()) == expected_tools

        # Should NOT have mutative tools
        mutative_tools = {
            "add_cron_job",
            "remove_cron_job",
            "list_cron_jobs",
            "add_context",
            "open_data_request_ticket",
        }
        for tool in mutative_tools:
            assert tool not in tools

    @pytest.mark.asyncio
    async def test_regular_message_has_all_tools(self, mock_bot):
        """Test that regular messages get all tools including mutative ones."""
        tools = await mock_bot.get_tools_for_message(
            channel="C123",
            message_ts="1234567890.123456",  # Non-None message_ts
            thread_ts="T1234",
            user="U123",
            is_automated_message=False,
        )

        # Should have read-only tools
        expected_readonly_tools = {
            "run_sql_query",
            "search_datasets",
            "search_context",
            "render_data_visualization",
            "search_web",
            "attach_csv",
        }
        for tool in expected_readonly_tools:
            assert tool in tools

        # Should also have cron tools (since message_ts is not None)
        mock_bot.cron_manager.get_cron_tools.assert_called_once_with(
            channel="C123", message_ts="1234567890.123456", user="U123"
        )

        # Should have mutative tools (add_context, open_data_request_ticket are added when message_ts is not None)
        expected_mutative_tools = {
            "add_cron_job",
            "remove_cron_job",
            "list_cron_jobs",
        }
        for tool in expected_mutative_tools:
            assert tool in tools

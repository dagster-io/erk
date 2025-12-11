"""
Test cases for governance channel warning behavior.

Tests governance channel warnings for plan limits and usage monitoring.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import SecretStr

from csbot.slackbot.channel_bot.bot import BotTypeQA, CompassChannelQANormalBotInstance
from csbot.slackbot.issue_creator.github import GithubIssueCreator
from csbot.slackbot.slackbot_core import AnthropicConfig, CompassBotServerConfig


class TestGovernanceChannelWarning:
    """Test cases for governance channel warning functionality."""

    @pytest.fixture
    def mock_bot_key(self):
        """Create mock bot key."""
        mock_key = Mock()
        mock_key.to_bot_id.return_value = "test_governance_bot"
        return mock_key

    @pytest.fixture
    def governance_bot(self, mock_bot_key):
        """Create minimal bot instance for testing governance warnings."""
        mock_client = AsyncMock()
        mock_kv_store = AsyncMock()

        # Create minimal bot instance for testing governance warnings
        server_config = Mock(CompassBotServerConfig)
        server_config.thread_health_inspector_config = None

        bot = CompassChannelQANormalBotInstance(
            key=mock_bot_key,
            logger=Mock(),
            github_config=Mock(),
            local_context_store=Mock(),
            client=mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=AnthropicConfig(
                provider="anthropic",
                api_key=SecretStr("test_api_key"),
                model="claude-sonnet-4-20250514",
            ),
            kv_store=mock_kv_store,
            governance_alerts_channel="governance-alerts",
            analytics_store=AsyncMock(),
            profile=Mock(),
            csbot_client=Mock(),
            data_request_github_creds=Mock(),
            slackbot_github_monitor=Mock(),
            scaffold_branch_enabled=False,
            bot_config=Mock(),
            bot_type=BotTypeQA(),
            server_config=server_config,
            storage=Mock(),
            issue_creator=GithubIssueCreator(Mock()),
        )

        # Store references for test access
        bot._test_client = mock_client  # type: ignore[attr-defined]
        bot._test_kv_store = mock_kv_store  # type: ignore[attr-defined]

        return bot

    @pytest.mark.asyncio
    async def test_send_governance_plan_limit_warning_success(self, governance_bot):
        """Test successful governance channel warning."""
        with patch(
            "csbot.slackbot.webapp.billing.urls.create_billing_management_url"
        ) as mock_billing_url:
            mock_billing_url.return_value = "https://example.com/billing/test-token"

            # Mock successful channel ID lookup
            governance_bot._test_kv_store.get_channel_id.return_value = "C999888777"

            # Call the governance warning method
            await governance_bot._send_governance_plan_limit_warning(
                limit=10, current_usage=10, user_channel="C123456789"
            )

            # Verify channel ID lookup
            governance_bot._test_kv_store.get_channel_id.assert_called_once_with(
                "governance-alerts"
            )

            # Verify governance message was sent
            governance_bot._test_client.chat_postMessage.assert_called_once()
            call_args = governance_bot._test_client.chat_postMessage.call_args
            assert call_args[1]["channel"] == "C999888777"
            assert "*Compass plan limit reached*" in call_args[1]["text"]
            assert "<#C123456789>" in call_args[1]["text"]
            assert "10 answers for this month" in call_args[1]["text"]

            # Verify blocks were sent with text
            assert "blocks" in call_args[1]
            blocks = call_args[1]["blocks"]
            assert len(blocks) == 1

            # Verify the text block structure
            text_block = blocks[0]
            assert text_block["type"] == "section"
            assert text_block["text"]["type"] == "mrkdwn"
            assert "⚠️ *Compass plan limit reached*" in text_block["text"]["text"]

    @pytest.mark.asyncio
    async def test_send_governance_plan_limit_warning_no_channel_id(self, governance_bot):
        """Test governance warning when channel ID cannot be found."""
        with patch(
            "csbot.slackbot.webapp.billing.urls.create_billing_management_url"
        ) as mock_billing_url:
            mock_billing_url.return_value = "https://example.com/billing/test-token"

            # Mock failed channel ID lookup
            governance_bot._test_kv_store.get_channel_id.return_value = None

            # Call the governance warning method
            await governance_bot._send_governance_plan_limit_warning(
                limit=10, current_usage=10, user_channel="C123456789"
            )

            # Verify channel ID lookup was attempted
            governance_bot._test_kv_store.get_channel_id.assert_called_once_with(
                "governance-alerts"
            )

            # Verify no message was sent
            governance_bot._test_client.chat_postMessage.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_governance_plan_limit_warning_exception(self, governance_bot):
        """Test governance warning handles exceptions gracefully."""
        with patch(
            "csbot.slackbot.webapp.billing.urls.create_billing_management_url"
        ) as mock_billing_url:
            mock_billing_url.return_value = "https://example.com/billing/test-token"

            # Mock exception during channel ID lookup
            governance_bot._test_kv_store.get_channel_id.side_effect = Exception(
                "Channel lookup failed"
            )

            # Call the governance warning method - should not raise
            await governance_bot._send_governance_plan_limit_warning(
                limit=10, current_usage=10, user_channel="C123456789"
            )

            # Verify no message was sent
            governance_bot._test_client.chat_postMessage.assert_not_called()

"""Test cases for channel creation welcome message functionality.

This module tests the integration of welcome message sending with channel creation flows.
It focuses on verifying that create_channel_and_bot_instance properly calls the welcome message function.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from csbot.slackbot.slack_utils import create_channel_and_bot_instance


class TestChannelCreationWelcomeMessageIntegration:
    """Tests for welcome message integration with create_channel_and_bot_instance."""

    @pytest.mark.asyncio
    async def test_create_channel_and_bot_instance_calls_welcome_message(self):
        """Test that create_channel_and_bot_instance calls the welcome message function after channel creation."""
        # Mock all the external API calls but let the actual function run
        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post_api:
            with patch(
                "csbot.slackbot.slack_utils._send_channel_creation_welcome_message"
            ) as mock_welcome:
                # Mock SlackstreamMessage imports to prevent import failures
                with patch("csbot.slackbot.slackbot_slackstream.SlackstreamMessage"):
                    # Mock successful API responses for channel creation flow
                    mock_post_api.side_effect = [
                        {
                            "success": True,
                            "channels": [],
                            "channel_name_to_id": {},
                        },  # get_all_channels (checking existing)
                        {
                            "success": True,
                            "channel": {"id": "C987654321", "name": "test-channel"},
                        },  # Create channel
                        {"success": True, "user_id": "B111111111"},  # Get bot user for dev tools
                        {"success": True, "user_id": "B222222222"},  # Get bot user for compass
                        {"success": True},  # Invite dev tools bot
                        {"success": True},  # Invite compass bot
                    ]

                    # Mock governance bot
                    governance_bot = Mock()
                    governance_bot.governance_alerts_channel = "governance"
                    governance_bot.bot_server = Mock()
                    governance_bot.bot_server.bot_manager = Mock()
                    governance_bot.bot_server.bot_manager.discover_and_update_bots_for_keys = (
                        AsyncMock()
                    )
                    governance_bot.bot_server.channel_id_to_name = {}  # Mock the dictionary properly

                    # Mock the bot instance that will be retrieved after discovery
                    mock_bot_instance = Mock()
                    mock_bot_instance.associate_channel_id = AsyncMock()
                    governance_bot.bot_server.bots = Mock()
                    governance_bot.bot_server.bots.get = Mock(return_value=mock_bot_instance)

                    governance_bot.client = Mock()
                    governance_bot.kv_store = AsyncMock()
                    governance_bot.kv_store.get_channel_id.return_value = (
                        None  # No governance channel found
                    )

                    # Mock storage
                    from csbot.slackbot.storage.interface import Organization

                    mock_org = Organization(
                        organization_id=123,
                        organization_name="Test Org",
                        organization_industry=None,
                        stripe_customer_id=None,
                        stripe_subscription_id=None,
                        has_governance_channel=True,
                        contextstore_github_repo="test-org/test-context",
                    )

                    storage = Mock()
                    storage.create_bot_instance = AsyncMock()
                    storage.list_organizations = AsyncMock(return_value=[mock_org])

                    logger = Mock()

                    result = await create_channel_and_bot_instance(
                        bot_server=governance_bot.bot_server,
                        channel_name="test-channel",
                        user_id="U123456789",
                        team_id="T123456789",
                        organization_id=123,
                        storage=storage,
                        governance_bot=governance_bot,
                        contextstore_github_repo="org/repo",
                        dev_tools_bot_token="xoxb-dev-token",
                        admin_token="xoxp-admin-token",
                        compass_bot_token="xoxb-compass-token",
                        logger=logger,
                        token=None,
                        has_valid_token=False,
                    )

                    # Should return success
                    assert result["success"] is True

                    # Should call welcome message function with correct parameters
                    mock_welcome.assert_called_once_with(
                        channel_id="C987654321",
                        compass_bot_token="xoxb-compass-token",
                        logger=logger,
                    )

    @pytest.mark.asyncio
    async def test_create_channel_and_bot_instance_welcome_message_failure_resilience(self):
        """Test that create_channel_and_bot_instance continues successfully even if welcome message has internal failures."""

        # This test simulates the actual welcome message function having internal failures
        # but still continuing execution (since _send_channel_creation_welcome_message handles its own exceptions)
        async def mock_welcome_with_failure(*args, **kwargs):
            # Simulate what the real function does - log warning but don't raise exception
            logger = kwargs.get("logger") or args[2] if len(args) > 2 else Mock()
            logger.warning(
                "Failed to send channel creation welcome message to test-channel: Simulated failure"
            )

        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post_api:
            with patch(
                "csbot.slackbot.slack_utils._send_channel_creation_welcome_message"
            ) as mock_welcome:
                # Mock SlackstreamMessage imports to prevent import failures
                with patch("csbot.slackbot.slackbot_slackstream.SlackstreamMessage"):
                    # Make welcome message simulate internal failure but not raise exception
                    mock_welcome.side_effect = mock_welcome_with_failure

                    # Mock successful API responses
                    mock_post_api.side_effect = [
                        {
                            "success": True,
                            "channels": [],
                            "channel_name_to_id": {},
                        },  # get_all_channels (checking existing)
                        {"success": True, "channel": {"id": "C987654321", "name": "test-channel"}},
                        {"success": True, "user_id": "B111111111"},
                        {"success": True, "user_id": "B222222222"},
                        {"success": True},
                        {"success": True},
                    ]

                    # Mock governance bot
                    governance_bot = Mock()
                    governance_bot.governance_alerts_channel = "governance"
                    governance_bot.bot_server = Mock()
                    governance_bot.bot_server.bot_manager = Mock()
                    governance_bot.bot_server.bot_manager.discover_and_update_bots_for_keys = (
                        AsyncMock()
                    )
                    governance_bot.bot_server.channel_id_to_name = {}  # Mock the dictionary properly

                    # Mock the bot instance that will be retrieved after discovery
                    mock_bot_instance = Mock()
                    mock_bot_instance.associate_channel_id = AsyncMock()
                    governance_bot.bot_server.bots = Mock()
                    governance_bot.bot_server.bots.get = Mock(return_value=mock_bot_instance)

                    governance_bot.client = Mock()
                    governance_bot.kv_store = AsyncMock()
                    governance_bot.kv_store.get_channel_id.return_value = None

                    # Mock storage
                    from csbot.slackbot.storage.interface import Organization

                    mock_org = Organization(
                        organization_id=123,
                        organization_name="Test Org",
                        organization_industry=None,
                        stripe_customer_id=None,
                        stripe_subscription_id=None,
                        has_governance_channel=True,
                        contextstore_github_repo="test-org/test-context",
                    )

                    storage = Mock()
                    storage.create_bot_instance = AsyncMock()
                    storage.list_organizations = AsyncMock(return_value=[mock_org])

                    logger = Mock()

                    # Should not raise exception despite welcome message internal failure
                    result = await create_channel_and_bot_instance(
                        bot_server=governance_bot.bot_server,
                        channel_name="test-channel",
                        user_id="U123456789",
                        team_id="T123456789",
                        organization_id=123,
                        storage=storage,
                        governance_bot=governance_bot,
                        contextstore_github_repo="org/repo",
                        dev_tools_bot_token="xoxb-dev-token",
                        admin_token="xoxp-admin-token",
                        compass_bot_token="xoxb-compass-token",
                        logger=logger,
                        token=None,
                        has_valid_token=False,
                    )

                    # Welcome message should have been attempted
                    mock_welcome.assert_called_once()

                    # Channel creation should still succeed
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_channel_and_bot_instance_welcome_message_timing(self):
        """Test that welcome message is called after bot discovery in the correct order."""
        call_order = []

        async def track_bot_discovery(*_args, **_kwargs):
            call_order.append("bot_discovery")

        async def track_welcome_message(*_args, **_kwargs):
            call_order.append("welcome_message")

        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post_api:
            with patch(
                "csbot.slackbot.slack_utils._send_channel_creation_welcome_message"
            ) as mock_welcome:
                # Mock SlackstreamMessage imports to prevent import failures
                with patch("csbot.slackbot.slackbot_slackstream.SlackstreamMessage"):
                    mock_welcome.side_effect = track_welcome_message

                    # Mock successful API responses
                    mock_post_api.side_effect = [
                        {
                            "success": True,
                            "channels": [],
                            "channel_name_to_id": {},
                        },  # get_all_channels (checking existing)
                        {"success": True, "channel": {"id": "C987654321", "name": "test-channel"}},
                        {"success": True, "user_id": "B111111111"},
                        {"success": True, "user_id": "B222222222"},
                        {"success": True},
                        {"success": True},
                    ]

                    # Mock governance bot with call tracking
                    governance_bot = Mock()
                    governance_bot.governance_alerts_channel = "governance"
                    governance_bot.bot_server = Mock()
                    governance_bot.bot_server.bot_manager = Mock()
                    discover_mock = AsyncMock()
                    discover_mock.side_effect = track_bot_discovery
                    governance_bot.bot_server.bot_manager.discover_and_update_bots_for_keys = (
                        discover_mock
                    )
                    governance_bot.bot_server.channel_id_to_name = {}  # Mock the dictionary properly

                    # Mock the bot instance that will be retrieved after discovery
                    mock_bot_instance = Mock()
                    mock_bot_instance.associate_channel_id = AsyncMock()
                    governance_bot.bot_server.bots = Mock()
                    governance_bot.bot_server.bots.get = Mock(return_value=mock_bot_instance)

                    governance_bot.client = Mock()
                    governance_bot.kv_store = AsyncMock()
                    governance_bot.kv_store.get_channel_id.return_value = None

                    # Mock storage
                    from csbot.slackbot.storage.interface import Organization

                    mock_org = Organization(
                        organization_id=123,
                        organization_name="Test Org",
                        organization_industry=None,
                        stripe_customer_id=None,
                        stripe_subscription_id=None,
                        has_governance_channel=True,
                        contextstore_github_repo="test-org/test-context",
                    )

                    storage = Mock()
                    storage.create_bot_instance = AsyncMock()
                    storage.list_organizations = AsyncMock(return_value=[mock_org])

                    logger = Mock()

                    await create_channel_and_bot_instance(
                        bot_server=governance_bot.bot_server,
                        channel_name="test-channel",
                        user_id="U123456789",
                        team_id="T123456789",
                        organization_id=123,
                        storage=storage,
                        governance_bot=governance_bot,
                        contextstore_github_repo="org/repo",
                        dev_tools_bot_token="xoxb-dev-token",
                        admin_token="xoxp-admin-token",
                        compass_bot_token="xoxb-compass-token",
                        logger=logger,
                        token=None,
                        has_valid_token=False,
                    )

                    # Welcome message should be called after bot discovery
                    assert call_order == ["bot_discovery", "welcome_message"]

    @pytest.mark.asyncio
    async def test_create_channel_uses_combined_bot_when_has_governance_channel_false(self):
        """Test that create_channel_and_bot_instance creates combined bot when has_governance_channel=False."""
        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post_api:
            with patch("csbot.slackbot.slack_utils._send_channel_creation_welcome_message"):
                with patch("csbot.slackbot.slackbot_slackstream.SlackstreamMessage"):
                    mock_post_api.side_effect = [
                        {"success": True, "channels": [], "channel_name_to_id": {}},
                        {"success": True, "channel": {"id": "C987654321", "name": "test-channel"}},
                        {"success": True, "user_id": "B111111111"},
                        {"success": True, "user_id": "B222222222"},
                        {"success": True},
                        {"success": True},
                    ]

                    # Mock governance bot (shouldn't be used for combined bots)
                    governance_bot = Mock()
                    governance_bot.governance_alerts_channel = "governance"
                    governance_bot.bot_server = Mock()
                    governance_bot.bot_server.bot_manager = Mock()
                    governance_bot.bot_server.bot_manager.discover_and_update_bots_for_keys = (
                        AsyncMock()
                    )
                    governance_bot.bot_server.channel_id_to_name = {}

                    mock_bot_instance = Mock()
                    mock_bot_instance.associate_channel_id = AsyncMock()
                    governance_bot.bot_server.bots = Mock()
                    governance_bot.bot_server.bots.get = Mock(return_value=mock_bot_instance)

                    # Mock storage with organization that has has_governance_channel=False
                    from csbot.slackbot.storage.interface import Organization

                    mock_org = Organization(
                        organization_id=123,
                        organization_name="Test Org",
                        organization_industry=None,
                        stripe_customer_id=None,
                        stripe_subscription_id=None,
                        has_governance_channel=False,
                        contextstore_github_repo="test-org/test-context",
                    )

                    storage = Mock()
                    storage.create_bot_instance = AsyncMock()
                    storage.list_organizations = AsyncMock(return_value=[mock_org])

                    logger = Mock()

                    result = await create_channel_and_bot_instance(
                        bot_server=governance_bot.bot_server,
                        channel_name="test-channel",
                        user_id="U123456789",
                        team_id="T123456789",
                        organization_id=123,
                        storage=storage,
                        governance_bot=governance_bot,
                        contextstore_github_repo="org/repo",
                        dev_tools_bot_token="xoxb-dev-token",
                        admin_token="xoxp-admin-token",
                        compass_bot_token="xoxb-compass-token",
                        logger=logger,
                        token=None,
                        has_valid_token=False,
                    )

                    assert result["success"] is True

                    # Verify bot instance was created with combined model (governance_alerts_channel = channel_name)
                    storage.create_bot_instance.assert_called_once()
                    call_kwargs = storage.create_bot_instance.call_args.kwargs
                    assert call_kwargs["channel_name"] == "test-channel"
                    assert call_kwargs["governance_alerts_channel"] == "test-channel"

    @pytest.mark.asyncio
    async def test_create_channel_uses_separate_governance_when_has_governance_channel_true(self):
        """Test that create_channel_and_bot_instance uses separate governance channel when has_governance_channel=True."""
        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post_api:
            with patch("csbot.slackbot.slack_utils._send_channel_creation_welcome_message"):
                with patch("csbot.slackbot.slackbot_slackstream.SlackstreamMessage"):
                    mock_post_api.side_effect = [
                        {"success": True, "channels": [], "channel_name_to_id": {}},
                        {"success": True, "channel": {"id": "C987654321", "name": "test-channel"}},
                        {"success": True, "user_id": "B111111111"},
                        {"success": True, "user_id": "B222222222"},
                        {"success": True},
                        {"success": True},
                    ]

                    # Mock governance bot with separate governance channel
                    governance_bot = Mock()
                    governance_bot.governance_alerts_channel = "governance-alerts"
                    governance_bot.bot_server = Mock()
                    governance_bot.bot_server.bot_manager = Mock()
                    governance_bot.bot_server.bot_manager.discover_and_update_bots_for_keys = (
                        AsyncMock()
                    )
                    governance_bot.bot_server.channel_id_to_name = {}

                    mock_bot_instance = Mock()
                    mock_bot_instance.associate_channel_id = AsyncMock()
                    governance_bot.bot_server.bots = Mock()
                    governance_bot.bot_server.bots.get = Mock(return_value=mock_bot_instance)

                    # Mock storage with organization that has has_governance_channel=True
                    from csbot.slackbot.storage.interface import Organization

                    mock_org = Organization(
                        organization_id=123,
                        organization_name="Test Org",
                        organization_industry=None,
                        stripe_customer_id=None,
                        stripe_subscription_id=None,
                        has_governance_channel=True,
                        contextstore_github_repo="test-org/test-context",
                    )

                    storage = Mock()
                    storage.create_bot_instance = AsyncMock()
                    storage.list_organizations = AsyncMock(return_value=[mock_org])

                    logger = Mock()

                    result = await create_channel_and_bot_instance(
                        bot_server=governance_bot.bot_server,
                        channel_name="test-channel",
                        user_id="U123456789",
                        team_id="T123456789",
                        organization_id=123,
                        storage=storage,
                        governance_bot=governance_bot,
                        contextstore_github_repo="org/repo",
                        dev_tools_bot_token="xoxb-dev-token",
                        admin_token="xoxp-admin-token",
                        compass_bot_token="xoxb-compass-token",
                        logger=logger,
                        token=None,
                        has_valid_token=False,
                    )

                    assert result["success"] is True

                    # Verify bot instance was created with separate governance model
                    storage.create_bot_instance.assert_called_once()
                    call_kwargs = storage.create_bot_instance.call_args.kwargs
                    assert call_kwargs["channel_name"] == "test-channel"
                    assert call_kwargs["governance_alerts_channel"] == "governance-alerts"

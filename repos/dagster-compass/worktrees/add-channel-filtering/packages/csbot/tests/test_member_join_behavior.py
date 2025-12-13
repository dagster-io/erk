"""Test cases for member join behavior functionality.

This module tests member join related functionality including:
- Member join incentive processing (bonus grants)
- Governance welcome message generation
- JWT token validation for connection management buttons
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import SecretStr

from csbot.slackbot.admin_commands import AdminCommands
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import (
    BotTypeGovernance,
    BotTypeQA,
    CompassChannelGovernanceBotInstance,
    CompassChannelQANormalBotInstance,
)
from csbot.slackbot.slackbot_analytics import USER_GRANT_AMOUNT
from csbot.slackbot.slackbot_blockkit import ActionsBlock, ButtonElement, SectionBlock
from csbot.slackbot.slackbot_core import AnthropicConfig
from csbot.slackbot.storage.onboarding_state import BotInstanceType
from tests.utils.slack_client import FakeSlackClient


@pytest.fixture
def base_bot_config():
    """Create base bot configuration shared across tests."""
    mock_key = Mock()
    mock_key.to_bot_id.return_value = "test_bot_id"

    mock_ai_config = AnthropicConfig(
        provider="anthropic",
        api_key=SecretStr("test_api_key"),
        model="claude-sonnet-4-20250514",
    )

    return {
        "key": mock_key,
        "logger": Mock(),
        "github_config": Mock(),
        "local_context_store": Mock(),
        "ai_config": mock_ai_config,
        "kv_store": AsyncMock(),
        "governance_alerts_channel": "governance",
        "profile": Mock(),
        "csbot_client": Mock(),
        "data_request_github_creds": Mock(),
        "slackbot_github_monitor": Mock(),
        "scaffold_branch_enabled": False,
        "bot_type": BotTypeQA(),
        "bot_background_task_manager": AsyncMock(),
        "server_config": Mock(),
        "storage": Mock(),
        "issue_creator": AsyncMock(),
    }


class TestMemberJoinIncentive:
    """Test cases for _process_member_join_incentive functionality."""

    @pytest.fixture
    def bot_with_incentive_deps(self, base_bot_config):
        """Create a bot instance with dependencies for incentive testing."""
        # Add incentive-specific dependencies
        mock_client = AsyncMock()
        mock_analytics_store = AsyncMock()
        mock_bot_config = Mock()
        mock_bot_config.organization_id = 123

        bot_config = {
            **base_bot_config,
            "client": mock_client,
            "analytics_store": mock_analytics_store,
            "bot_config": mock_bot_config,
        }

        bot = CompassChannelQANormalBotInstance(**bot_config)

        # Store mocks in a dictionary that tests can access
        return {
            "bot": bot,
            "mock_client": mock_client,
            "mock_analytics_store": mock_analytics_store,
            "mock_logger": bot_config["logger"],
        }

    @pytest.mark.asyncio
    async def test_successful_incentive_for_external_user(self, bot_with_incentive_deps):
        """Test successful bonus grant for external user."""
        from unittest.mock import patch

        from csbot.slackbot.channel_bot.personalization import SlackUserInfo

        bot = bot_with_incentive_deps["bot"]
        mock_analytics_store = bot_with_incentive_deps["mock_analytics_store"]
        mock_logger = bot_with_incentive_deps["mock_logger"]

        # Mock get_cached_user_info to return external user
        mock_user_info = SlackUserInfo(
            real_name="External User",
            username="external.user",
            email="user@external.com",
            avatar_url=None,
            timezone=None,
            is_bot=False,
            is_admin=False,
            is_owner=False,
            deleted=False,
            is_restricted=False,
            is_ultra_restricted=False,
        )

        # Mock existing grants below limit
        mock_analytics_store.get_bonus_grants_by_reason.return_value = 50

        with patch(
            "csbot.slackbot.channel_bot.bot.get_cached_user_info", return_value=mock_user_info
        ):
            # Call the method
            await bot._process_member_join_incentive("U123456789")

        # Verify analytics store calls
        mock_analytics_store.get_bonus_grants_by_reason.assert_called_once_with(
            123, "slack member incentive"
        )
        mock_analytics_store.create_bonus_answer_grant.assert_called_once_with(
            123, USER_GRANT_AMOUNT, "slack member incentive"
        )

        # Verify logging
        mock_logger.info.assert_called_once()
        info_call = mock_logger.info.call_args[0][0]
        assert f"Added {USER_GRANT_AMOUNT} bonus answers" in info_call
        assert "U123456789" in info_call

    @pytest.mark.asyncio
    async def test_skip_bot_user(self, bot_with_incentive_deps):
        """Test that bot users are skipped."""
        from unittest.mock import patch

        from csbot.slackbot.channel_bot.personalization import SlackUserInfo

        bot = bot_with_incentive_deps["bot"]
        mock_analytics_store = bot_with_incentive_deps["mock_analytics_store"]
        mock_logger = bot_with_incentive_deps["mock_logger"]

        # Mock get_cached_user_info to return bot user
        mock_user_info = SlackUserInfo(
            real_name="Bot User",
            username="bot.user",
            email="bot@external.com",
            avatar_url=None,
            timezone=None,
            is_bot=True,
            is_admin=False,
            is_owner=False,
            deleted=False,
            is_restricted=False,
            is_ultra_restricted=False,
        )

        with patch(
            "csbot.slackbot.channel_bot.bot.get_cached_user_info", return_value=mock_user_info
        ):
            # Call the method
            await bot._process_member_join_incentive("B123456789")

        # Verify no grant was created
        mock_analytics_store.create_bonus_answer_grant.assert_not_called()
        mock_analytics_store.get_bonus_grants_by_reason.assert_not_called()

        # Verify debug logging
        mock_logger.debug.assert_called_with("Skipping bot user B123456789")

    @pytest.mark.asyncio
    async def test_skip_dagster_employee(self, bot_with_incentive_deps):
        """Test that Dagster employees are skipped."""
        from unittest.mock import patch

        from csbot.slackbot.channel_bot.personalization import SlackUserInfo

        bot = bot_with_incentive_deps["bot"]
        mock_analytics_store = bot_with_incentive_deps["mock_analytics_store"]
        mock_logger = bot_with_incentive_deps["mock_logger"]

        # Mock get_cached_user_info to return Dagster employee
        mock_user_info = SlackUserInfo(
            real_name="Dagster Employee",
            username="dagster.employee",
            email="employee@dagsterlabs.com",
            avatar_url=None,
            timezone=None,
            is_bot=False,
            is_admin=False,
            is_owner=False,
            deleted=False,
            is_restricted=False,
            is_ultra_restricted=False,
        )

        with patch(
            "csbot.slackbot.channel_bot.bot.get_cached_user_info", return_value=mock_user_info
        ):
            # Call the method
            await bot._process_member_join_incentive("U123456789")

        # Verify no grant was created
        mock_analytics_store.create_bonus_answer_grant.assert_not_called()
        mock_analytics_store.get_bonus_grants_by_reason.assert_not_called()

        # Verify debug logging
        mock_logger.debug.assert_called_with(
            "Skipping Dagster employee U123456789 with email employee@dagsterlabs.com"
        )

    @pytest.mark.asyncio
    async def test_skip_when_at_grant_limit(self, bot_with_incentive_deps):
        """Test that grants are not created when at 100 grant limit."""
        from unittest.mock import patch

        from csbot.slackbot.channel_bot.personalization import SlackUserInfo

        bot = bot_with_incentive_deps["bot"]
        mock_analytics_store = bot_with_incentive_deps["mock_analytics_store"]
        mock_logger = bot_with_incentive_deps["mock_logger"]

        # Mock get_cached_user_info to return external user
        mock_user_info = SlackUserInfo(
            real_name="External User",
            username="external.user",
            email="user@external.com",
            avatar_url=None,
            timezone=None,
            is_bot=False,
            is_admin=False,
            is_owner=False,
            deleted=False,
            is_restricted=False,
            is_ultra_restricted=False,
        )

        # Mock existing grants at limit
        mock_analytics_store.get_bonus_grants_by_reason.return_value = 100

        with patch(
            "csbot.slackbot.channel_bot.bot.get_cached_user_info", return_value=mock_user_info
        ):
            # Call the method
            await bot._process_member_join_incentive("U123456789")

        # Verify existing grants were checked
        mock_analytics_store.get_bonus_grants_by_reason.assert_called_once_with(
            123, "slack member incentive"
        )

        # Verify no grant was created
        mock_analytics_store.create_bonus_answer_grant.assert_not_called()

        # Verify debug logging
        mock_logger.debug.assert_called_with(
            "Already at maximum grants (100), not adding grant for U123456789"
        )


class TestGovernanceWelcomeMessage:
    """Tests for _build_governance_welcome_message functionality."""

    @pytest.fixture
    def bot_server_config(self):
        config = Mock()
        config.jwt_secret = Mock()
        config.jwt_secret.get_secret_value.return_value = "test-secret"
        config.public_url = "https://test.example.com"
        return config

    @pytest.fixture
    def bot_server(self, bot_base, bot_server_config):
        mock_bot_server = Mock()

        # Create a QA bot instance for the governed channel
        # This bot will be discovered by _get_organization_bots()
        qa_bot_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")
        qa_bot = Mock()
        qa_bot.bot_type = BotTypeQA()
        qa_bot.key = qa_bot_key
        qa_bot.profile = Mock()
        qa_bot.profile.connections = {}
        qa_bot.bot_config = Mock()
        qa_bot.bot_config.organization_id = 123
        qa_bot.bot_config.team_id = "T123456789"

        mock_bot_server.bots = {
            qa_bot_key: qa_bot,
            bot_base.key: bot_base,
        }
        mock_bot_server.config = bot_server_config
        return mock_bot_server

    @pytest.fixture
    def bot_base(self, base_bot_config, bot_server_config):
        """Create a bot instance configured for welcome message testing."""
        # Create minimal bot instance with mocked key and bot_server
        bot = CompassChannelGovernanceBotInstance.__new__(CompassChannelGovernanceBotInstance)
        bot.key = BotKey.from_channel_name(
            team_id="T123456789", channel_name="test-channel-governance"
        )

        # Mock bot_server with proper config for JWT token generation
        bot.client = AsyncMock()
        bot.bot_type = BotTypeGovernance(
            governed_bot_keys=set(
                [BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")]
            )
        )
        bot.server_config = bot_server_config

        # Add bot_config needed by _get_organization_bots()
        bot.bot_config = Mock()
        bot.bot_config.organization_id = 123
        bot.bot_config.team_id = "T123456789"

        return bot

    @pytest.fixture
    def bot_with_connections(self, bot_base, bot_server):
        """Create a bot with warehouse connections."""
        bot_base.profile = Mock()
        bot_base.profile.connections = {
            "bigquery_conn": Mock(),
            "postgres_conn": Mock(),
        }
        # Also set connections on the QA bot in bot_server
        qa_bot_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")
        bot_server.bots[qa_bot_key].profile.connections = bot_base.profile.connections
        return bot_base

    @pytest.fixture
    def bot_without_connections(self, bot_base, bot_server):
        """Create a bot without warehouse connections."""
        bot_base.profile = Mock()
        bot_base.profile.connections = {}
        # QA bot already has empty connections from bot_server fixture
        return bot_base

    @pytest.fixture
    def bot_no_connections(self, bot_base, bot_server):
        """Create a bot with no connections (same as bot_without_connections)."""
        bot_base.profile = Mock()
        bot_base.profile.connections = {}
        # QA bot already has empty connections from bot_server fixture
        return bot_base

    @pytest.fixture
    def bot_without_connections_alt(self, bot_base, bot_server):
        """Create a bot without warehouse connections (alternate fixture)."""
        bot_base.profile = Mock()
        bot_base.profile.connections = {}
        # QA bot already has empty connections from bot_server fixture
        return bot_base

    def test_welcome_message_with_connections_returns_text_only(
        self, bot_with_connections, bot_server
    ):
        """Test that when connections exist, only text is returned (no button)."""
        result = AdminCommands(bot_with_connections, bot_server)._build_governance_welcome_message(
            "U123456789", "C987654321"
        )

        # Should be a sequence of blocks with only one SectionBlock (no button)
        assert isinstance(result, (list | tuple))
        assert len(result) == 1

        # First block should be a SectionBlock
        section_block = result[0]
        assert isinstance(section_block, SectionBlock)
        assert section_block.text is not None

        # Check message content
        expected_text = (
            "👋 Welcome to the Compass governance channel, <@U123456789>!\n\n"
            "- This channel administers the Compass bot running in <#C987654321>, including managing warehouse connections and the context store.\n"
            "- To get started, type !admin into the channel."
        )
        assert section_block.text.text == expected_text

    def test_welcome_message_without_connections_returns_button(
        self, bot_without_connections, bot_server
    ):
        """Test that when no connections exist, a button is included."""
        result = AdminCommands(
            bot_without_connections, bot_server
        )._build_governance_welcome_message("U123456789", "C987654321")

        # Should be a sequence of blocks with HeaderBlock, 3 SectionBlocks, DividerBlock, ActionsBlock, and ContextBlock
        assert isinstance(result, (list | tuple))
        assert len(result) == 7

        # First block should be header
        header_block = result[0]
        from csbot.slackbot.slackbot_blockkit import HeaderBlock

        assert isinstance(header_block, HeaderBlock)
        assert header_block.text.text == "Welcome to Compass 🎉"

        # Second block should be section with greeting
        expected_text = "👋 Hi there. I'm Compass. Welcome to your governance channel."
        section_block = result[1]
        assert isinstance(section_block, SectionBlock)
        assert section_block.text is not None
        assert section_block.text.text == expected_text

        # Sixth block should be actions with button (only connect button since no sample data config)
        actions_block = result[5]
        assert isinstance(actions_block, ActionsBlock)
        assert actions_block.elements is not None
        assert len(actions_block.elements) == 1

        button = actions_block.elements[0]
        assert isinstance(button, ButtonElement)
        assert button.text is not None
        assert button.text.text == "🔗 Connect your data"

    def test_button_opens_modal_instead_of_url(self, bot_without_connections, bot_server):
        """Test that the connection button opens a modal instead of using a URL."""
        result = AdminCommands(
            bot_without_connections, bot_server
        )._build_governance_welcome_message("U123456789", "C987654321")

        # Extract button from actions block (sixth block, second element)
        actions_block = result[5]
        assert isinstance(actions_block, ActionsBlock)
        assert actions_block.elements is not None
        # Sample data button is first, connection button is second
        button = actions_block.elements[-1]
        assert isinstance(button, ButtonElement)

        # Button should have modal interaction config instead of URL
        assert button.url is None
        assert button.action_id is not None
        assert button.value is not None

        # Verify action_id format for modal interaction
        assert button.action_id.startswith("show_managed_modal:")

        # Verify value contains modal type and user_id
        import json

        value_data = json.loads(button.value)
        assert value_data["managed_modal_type"] == "connection_management_modal"
        assert value_data["props"]["user_id"] == "U123456789"

    def test_button_contains_user_id_in_props(self, bot_without_connections, bot_server):
        """Test that the button contains the correct user_id in modal props."""
        result = AdminCommands(
            bot_without_connections, bot_server
        )._build_governance_welcome_message("U123456789", "C987654321")

        # Extract button from actions block
        actions_block = result[5]
        assert isinstance(actions_block, ActionsBlock)
        assert actions_block.elements is not None
        button = actions_block.elements[-1]
        assert isinstance(button, ButtonElement)

        # Verify modal interaction properties
        assert button.value is not None
        import json

        value_data = json.loads(button.value)

        # Should have the correct modal type
        assert value_data["managed_modal_type"] == "connection_management_modal"

        # Should have user_id in props
        assert "props" in value_data
        assert value_data["props"]["user_id"] == "U123456789"

    def test_button_text_is_correct(self, bot_without_connections, bot_server):
        """Test that the button has the correct text for connecting data."""
        result = AdminCommands(
            bot_without_connections, bot_server
        )._build_governance_welcome_message("U123456789", "C987654321")

        # Extract button from actions block
        actions_block = result[5]
        assert isinstance(actions_block, ActionsBlock)
        assert actions_block.elements is not None
        button = actions_block.elements[-1]
        assert isinstance(button, ButtonElement)

        # Verify button text
        assert button.text is not None
        assert button.text.text == "🔗 Connect your data"

    def test_welcome_message_with_sample_data_shows_both_buttons(
        self, bot_without_connections_alt, bot_server
    ):
        """Test that when no connections exist, only the connection button is shown."""
        result = AdminCommands(
            bot_without_connections_alt,
            bot_server,
        )._build_governance_welcome_message("U123456789", "C987654321")

        # Should be a sequence of blocks with HeaderBlock, 3 SectionBlocks, DividerBlock, ActionsBlock, and ContextBlock
        assert isinstance(result, (list | tuple))
        assert len(result) == 7

        # First block should be header
        header_block = result[0]
        from csbot.slackbot.slackbot_blockkit import HeaderBlock

        assert isinstance(header_block, HeaderBlock)
        assert header_block.text.text == "Welcome to Compass 🎉"

        # Second block should be section with greeting
        expected_text = "👋 Hi there. I'm Compass. Welcome to your governance channel."
        section_block = result[1]
        assert isinstance(section_block, SectionBlock)
        assert section_block.text is not None
        assert section_block.text.text == expected_text

        # Sixth block should be actions with two buttons
        actions_block = result[5]
        assert isinstance(actions_block, ActionsBlock)
        assert actions_block.elements is not None
        assert len(actions_block.elements) == 1

        # Button should be the warehouse connection button (now opens modal)
        warehouse_button = actions_block.elements[0]
        assert isinstance(warehouse_button, ButtonElement)
        assert warehouse_button.text is not None
        assert warehouse_button.text.text == "🔗 Connect your data"

        # Button should open modal instead of using URL
        assert warehouse_button.url is None
        assert warehouse_button.action_id is not None
        assert warehouse_button.value is not None

        # Verify modal interaction config
        import json

        value_data = json.loads(warehouse_button.value)
        assert value_data["managed_modal_type"] == "connection_management_modal"
        assert value_data["props"]["user_id"] == "U123456789"


class TestMemberJoinWelcomeIntegration:
    """Integration tests for member join welcome message behavior."""

    @pytest.fixture
    def governance_bot_with_connections(self, base_bot_config):
        """Create a governance bot with warehouse connections."""
        # Create FakeSlackClient
        fake_client = FakeSlackClient(token="xoxb-test-token")

        # Create governance bot
        gov_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-governance")
        gov_bot = CompassChannelGovernanceBotInstance.__new__(CompassChannelGovernanceBotInstance)
        gov_bot.key = gov_key
        gov_bot.client = fake_client  # type: ignore[assignment]
        gov_bot.logger = Mock()

        # Create regular bot with connections
        regular_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")
        regular_bot = CompassChannelQANormalBotInstance.__new__(CompassChannelQANormalBotInstance)
        regular_bot.key = regular_key
        regular_bot.profile = Mock()
        regular_bot.profile.connections = {"bigquery_conn": Mock()}
        regular_bot.bot_type = BotTypeQA()

        # Add bot_config needed by _get_organization_bots()
        regular_bot.bot_config = Mock()
        regular_bot.bot_config.organization_id = 123
        regular_bot.bot_config.team_id = "T123456789"

        mock_server_config = Mock()
        mock_server_config.jwt_secret = Mock()
        mock_server_config.jwt_secret.get_secret_value.return_value = "test-secret"
        mock_server_config.public_url = "https://test.example.com"

        # Set up bot server with both bots
        mock_bot_server = Mock()
        mock_bot_server.bots = {regular_key: regular_bot}
        mock_bot_server.bot_manager = Mock()
        mock_bot_server.bot_manager.storage = AsyncMock()
        mock_bot_server.bot_manager.storage.get_org_user_by_slack_user_id = AsyncMock(
            return_value=None
        )
        mock_bot_server.bot_manager.storage.add_org_user = AsyncMock()

        mock_bot_server.config = mock_server_config
        gov_bot.server_config = mock_server_config
        regular_bot.server_config = mock_server_config

        # Configure governance bot type
        gov_bot.bot_type = BotTypeGovernance(governed_bot_keys=set([regular_key]))
        gov_bot.governance_alerts_channel = "test-governance"  # governance channel name

        # Create governance and regular channels in FakeSlackClient
        # Note: We create channels manually to avoid asyncio.run in fixtures
        governance_channel_id = fake_client._generate_channel_id()
        fake_client._channels[governance_channel_id] = {
            "id": governance_channel_id,
            "name": "test-governance",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        regular_channel_id = fake_client._generate_channel_id()
        fake_client._channels[regular_channel_id] = {
            "id": regular_channel_id,
            "name": "test-channel",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        # Create a test user
        user = fake_client.create_test_user(
            name="Test User",
            email="user@external.com",
            is_bot=False,
        )
        # Use the generated user ID or force it to be U123456789
        user["id"] = "U123456789"
        fake_client._users["U123456789"] = user

        # Mock KV store to return correct channel IDs
        gov_bot.kv_store = AsyncMock()

        def kv_side_effect(channel_name):
            if channel_name == "test-governance":
                return governance_channel_id
            else:
                return regular_channel_id

        gov_bot.kv_store.get_channel_id.side_effect = kv_side_effect

        # Mock bot config - set different channel name to trigger governance logic
        gov_bot.bot_config = Mock()
        gov_bot.bot_config.channel_name = "test-channel"  # regular channel name
        gov_bot.bot_config.organization_id = 123

        # Mock additional methods needed by handle_member_joined_channel
        gov_bot.get_bot_user_id = AsyncMock(return_value="B987654321")
        gov_bot._log_analytics_event_with_context = AsyncMock()
        gov_bot._track_original_user_join_if_first_time = AsyncMock()
        gov_bot.analytics_store = AsyncMock()

        return gov_bot, fake_client, governance_channel_id, regular_channel_id, mock_bot_server

    @pytest.fixture
    def governance_bot_without_connections(self, base_bot_config):
        """Create a governance bot without warehouse connections."""
        # Create FakeSlackClient
        fake_client = FakeSlackClient(token="xoxb-test-token")

        # Create governance bot
        gov_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-governance")
        gov_bot = CompassChannelGovernanceBotInstance.__new__(CompassChannelGovernanceBotInstance)
        gov_bot.key = gov_key
        gov_bot.client = fake_client  # type: ignore[assignment]
        gov_bot.logger = Mock()

        # Create regular bot without connections
        regular_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")
        regular_bot = CompassChannelQANormalBotInstance.__new__(CompassChannelQANormalBotInstance)
        regular_bot.key = regular_key
        regular_bot.profile = Mock()
        regular_bot.profile.connections = {}  # No connections
        regular_bot.bot_type = BotTypeQA()

        # Add bot_config needed by _get_organization_bots()
        regular_bot.bot_config = Mock()
        regular_bot.bot_config.organization_id = 123
        regular_bot.bot_config.team_id = "T123456789"

        mock_server_config = Mock()
        mock_server_config.jwt_secret = Mock()
        mock_server_config.jwt_secret.get_secret_value.return_value = "test-secret"
        mock_server_config.public_url = "https://test.example.com"

        # Set up bot server
        mock_bot_server = Mock()
        mock_bot_server.bots = {regular_key: regular_bot}
        mock_bot_server.bot_manager = Mock()
        mock_bot_server.bot_manager.storage = AsyncMock()
        mock_bot_server.bot_manager.storage.get_org_user_by_slack_user_id = AsyncMock(
            return_value=None
        )
        mock_bot_server.bot_manager.storage.add_org_user = AsyncMock()

        mock_bot_server.config = mock_server_config
        regular_bot.server_config = mock_server_config
        gov_bot.server_config = mock_server_config

        # Configure governance bot type
        gov_bot.bot_type = BotTypeGovernance(governed_bot_keys=set([regular_key]))
        gov_bot.governance_alerts_channel = "test-governance"  # governance channel name

        # Create governance and regular channels in FakeSlackClient
        # Note: We create channels manually to avoid asyncio.run in fixtures
        governance_channel_id = fake_client._generate_channel_id()
        fake_client._channels[governance_channel_id] = {
            "id": governance_channel_id,
            "name": "test-governance",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        regular_channel_id = fake_client._generate_channel_id()
        fake_client._channels[regular_channel_id] = {
            "id": regular_channel_id,
            "name": "test-channel",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        # Create a test user
        user = fake_client.create_test_user(
            name="Test User",
            email="user@external.com",
            is_bot=False,
        )
        # Use the generated user ID or force it to be U123456789
        user["id"] = "U123456789"
        fake_client._users["U123456789"] = user

        # Mock KV store to return correct channel IDs
        gov_bot.kv_store = AsyncMock()

        def kv_side_effect(channel_name):
            if channel_name == "test-governance":
                return governance_channel_id
            else:
                return regular_channel_id

        gov_bot.kv_store.get_channel_id.side_effect = kv_side_effect

        # Mock bot config - set different channel name to trigger governance logic
        gov_bot.bot_config = Mock()
        gov_bot.bot_config.channel_name = "test-channel"  # regular channel name

        # Mock analytics store for member join incentive
        gov_bot.analytics_store = AsyncMock()
        gov_bot.bot_config.organization_id = 123

        # Mock additional methods needed by handle_member_joined_channel
        gov_bot.get_bot_user_id = AsyncMock(return_value="B987654321")
        gov_bot._log_analytics_event_with_context = AsyncMock()
        gov_bot._track_original_user_join_if_first_time = AsyncMock()

        return gov_bot, fake_client, governance_channel_id, regular_channel_id, mock_bot_server

    @pytest.mark.asyncio
    async def test_member_join_with_connections_sends_ephemeral(
        self, governance_bot_with_connections
    ):
        """Test that member join with connections sends ephemeral welcome message."""
        gov_bot, fake_client, governance_channel_id, regular_channel_id, bot_server = (
            governance_bot_with_connections
        )

        # Mock kv_store.get to return None (welcome message not yet sent)
        gov_bot.kv_store.get = AsyncMock(return_value=None)

        # Mock _process_member_join_incentive to avoid complex incentive logic
        gov_bot._process_member_join_incentive = AsyncMock()

        # Mock is_exempt_from_welcome_message to prevent regular welcome message
        with patch(
            "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=True
        ):
            # Call the member join handler
            event = {"user": "U123456789", "channel": governance_channel_id}
            await gov_bot.handle_member_joined_channel(bot_server, event)

        # Get ephemeral messages sent to the user
        ephemeral_messages = fake_client.get_ephemeral_messages(user_id="U123456789")
        assert len(ephemeral_messages) == 1

        # Check ephemeral message content
        ephemeral_msg = ephemeral_messages[0]
        assert "👋 Hi <@U123456789>" in ephemeral_msg["text"]
        assert "governance channel" in ephemeral_msg["text"]

        # Verify that welcome state was marked as sent
        gov_bot.kv_store.set.assert_called_with(
            "governance_welcome", f"channel:{governance_channel_id}", "true"
        )

    @pytest.mark.asyncio
    async def test_member_join_without_connections_sends_pinned_message(
        self, governance_bot_without_connections
    ):
        """Test that member join without connections sends and pins welcome message."""
        gov_bot, fake_client, governance_channel_id, regular_channel_id, bot_server = (
            governance_bot_without_connections
        )

        # Mock kv_store.get to return None (welcome message not yet sent)
        gov_bot.kv_store.get = AsyncMock(return_value=None)

        # Mock _process_member_join_incentive to avoid complex incentive logic
        gov_bot._process_member_join_incentive = AsyncMock()

        # Mock is_exempt_from_welcome_message to prevent regular welcome message
        with patch(
            "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=True
        ):
            # Call the member join handler
            event = {"user": "U123456789", "channel": governance_channel_id}
            await gov_bot.handle_member_joined_channel(bot_server, event)

        # Check that a message was posted with blocks (governance welcome message)
        channel_messages = fake_client.get_channel_messages(governance_channel_id)
        messages_with_blocks = [msg for msg in channel_messages if "blocks" in msg]
        assert len(messages_with_blocks) >= 1, "Should have posted governance welcome with blocks"

        # Check that the message was pinned
        pinned_items = await fake_client.pins_list(channel=governance_channel_id)
        assert len(pinned_items["items"]) >= 1, "Should have pinned the welcome message"

        # Verify no ephemeral messages were sent
        ephemeral_messages = fake_client.get_ephemeral_messages(user_id="U123456789")
        assert len(ephemeral_messages) == 0, (
            "Should not send ephemeral when governance channel has no connections"
        )

    @pytest.mark.asyncio
    async def test_governance_welcome_sends_ephemeral_when_already_sent_without_connections(
        self, governance_bot_without_connections
    ):
        """Test that governance sends compressed ephemeral if welcome already sent (even without connections)."""
        from csbot.slackbot.channel_bot.personalization import SlackUserInfo

        gov_bot, fake_client, governance_channel_id, regular_channel_id, bot_server = (
            governance_bot_without_connections
        )

        # Mock kv_store.get to return "true" (welcome message already sent)
        gov_bot.kv_store.get = AsyncMock(return_value="true")

        # Mock _process_member_join_incentive to avoid complex incentive logic
        gov_bot._process_member_join_incentive = AsyncMock()

        # Mock get_cached_user_info to avoid kv_store.set issues
        mock_user_info = SlackUserInfo(
            real_name="Test User",
            username="test.user",
            email="user@external.com",
            avatar_url=None,
            timezone=None,
            is_bot=False,
            is_admin=False,
            is_owner=False,
            deleted=False,
            is_restricted=False,
            is_ultra_restricted=False,
        )

        # Mock is_exempt_from_welcome_message to prevent regular welcome message
        with (
            patch(
                "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=True
            ),
            patch(
                "csbot.slackbot.channel_bot.bot.get_cached_user_info", return_value=mock_user_info
            ),
        ):
            # Call the member join handler
            event = {"user": "U123456789", "channel": governance_channel_id}
            await gov_bot.handle_member_joined_channel(bot_server, event)

        # Should send compressed ephemeral message (not full welcome)
        ephemeral_messages = fake_client.get_ephemeral_messages(user_id="U123456789")
        assert len(ephemeral_messages) == 1

        # Check ephemeral message content
        ephemeral_msg = ephemeral_messages[0]
        assert "👋 Hi <@U123456789>" in ephemeral_msg["text"]
        assert "governance channel" in ephemeral_msg["text"]

        # Verify no public messages were posted
        channel_messages = fake_client.get_channel_messages(governance_channel_id)
        assert len(channel_messages) == 0, "Should not post public message when already sent"

        # Verify no pins were added
        pinned_messages = [msg for msg in channel_messages if msg.get("pinned_to")]
        assert len(pinned_messages) == 0, "Should not pin any messages"

        # Should NOT mark as sent again (no call to set)
        gov_bot.kv_store.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_governance_channel_multiple_members_join(self):
        """Test governance channel with multiple users joining and welcome state tracking.

        Scenario:
        1. User 1 joins governance channel (no connections) -> gets pinned message, welcome marked as sent
        2. User 2 joins governance channel (welcome already sent) -> gets ephemeral message only
        3. First dataset is added (connection added to profile)
        4. User 3 joins governance channel (welcome already sent + connections) -> gets ephemeral message
        """
        # Create FakeSlackClient
        fake_client = FakeSlackClient(token="xoxb-test-token")

        # Create governance bot
        gov_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-governance")
        gov_bot = CompassChannelGovernanceBotInstance.__new__(CompassChannelGovernanceBotInstance)
        gov_bot.key = gov_key
        gov_bot.client = fake_client  # type: ignore[assignment]
        gov_bot.logger = Mock()

        # Create regular bot - starts with NO connections
        regular_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")
        regular_bot = CompassChannelQANormalBotInstance.__new__(CompassChannelQANormalBotInstance)
        regular_bot.key = regular_key
        regular_bot.profile = Mock()
        regular_bot.profile.connections = {}  # No connections initially
        regular_bot.bot_type = BotTypeQA()

        # Add bot_config needed by _get_organization_bots()
        regular_bot.bot_config = Mock()
        regular_bot.bot_config.organization_id = 123
        regular_bot.bot_config.team_id = "T123456789"

        # Set up bot server
        mock_bot_server = Mock()
        mock_bot_server.bots = {regular_key: regular_bot}
        mock_bot_server.bot_manager = Mock()
        mock_bot_server.bot_manager.storage = AsyncMock()
        mock_bot_server.bot_manager.storage.get_org_user_by_slack_user_id = AsyncMock(
            return_value=None
        )
        mock_bot_server.bot_manager.storage.add_org_user = AsyncMock()
        mock_bot_server.config = Mock()
        mock_bot_server.config.public_url = "https://test.example.com"

        mock_server_config = Mock()
        mock_server_config.jwt_secret = Mock()
        mock_server_config.jwt_secret.get_secret_value.return_value = "test-secret"

        # Configure governance bot type
        gov_bot.bot_type = BotTypeGovernance(governed_bot_keys=set([regular_key]))
        gov_bot.governance_alerts_channel = "test-governance"

        # Add bot_config to governance bot needed by _get_organization_bots()
        gov_bot.bot_config = Mock()
        gov_bot.bot_config.organization_id = 123
        gov_bot.bot_config.team_id = "T123456789"

        gov_bot.server_config = mock_server_config
        regular_bot.server_config = mock_server_config

        # Create channels manually
        governance_channel_id = fake_client._generate_channel_id()
        fake_client._channels[governance_channel_id] = {
            "id": governance_channel_id,
            "name": "test-governance",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        regular_channel_id = fake_client._generate_channel_id()
        fake_client._channels[regular_channel_id] = {
            "id": regular_channel_id,
            "name": "test-channel",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        # Create three test users
        user1 = fake_client.create_test_user(name="Alice", email="alice@external.com", is_bot=False)
        user1["id"] = "U111111111"
        fake_client._users["U111111111"] = user1

        user2 = fake_client.create_test_user(name="Bob", email="bob@external.com", is_bot=False)
        user2["id"] = "U222222222"
        fake_client._users["U222222222"] = user2

        user3 = fake_client.create_test_user(name="Carol", email="carol@external.com", is_bot=False)
        user3["id"] = "U333333333"
        fake_client._users["U333333333"] = user3

        # Create a real in-memory KV store to track state across member joins
        kv_storage = {}

        async def kv_get_channel_id(channel_name):
            if channel_name == "test-governance":
                return governance_channel_id
            else:
                return regular_channel_id

        async def kv_get(namespace, key):
            return kv_storage.get(f"{namespace}:{key}")

        async def kv_set(namespace, key, value, ttl=None):
            kv_storage[f"{namespace}:{key}"] = value

        gov_bot.kv_store = AsyncMock()
        gov_bot.kv_store.get_channel_id = AsyncMock(side_effect=kv_get_channel_id)
        gov_bot.kv_store.get = AsyncMock(side_effect=kv_get)
        gov_bot.kv_store.set = AsyncMock(side_effect=kv_set)

        # Mock bot config
        gov_bot.bot_config = Mock()
        gov_bot.bot_config.channel_name = "test-channel"
        gov_bot.bot_config.organization_id = 123

        # Mock additional methods
        gov_bot.get_bot_user_id = AsyncMock(return_value="B987654321")
        gov_bot._log_analytics_event_with_context = AsyncMock()
        gov_bot._track_original_user_join_if_first_time = AsyncMock()
        gov_bot._process_member_join_incentive = AsyncMock()
        gov_bot.analytics_store = AsyncMock()

        # STEP 1: User 1 joins (no connections) -> should get pinned message
        from csbot.slackbot.channel_bot.personalization import SlackUserInfo

        # Mock get_cached_user_info for all user joins
        def make_mock_user_info(name, email):
            return SlackUserInfo(
                real_name=name,
                username=name.lower(),
                email=email,
                avatar_url=None,
                timezone=None,
                is_bot=False,
                is_admin=False,
                is_owner=False,
                deleted=False,
                is_restricted=False,
                is_ultra_restricted=False,
            )

        with (
            patch(
                "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=True
            ),
            patch(
                "csbot.slackbot.channel_bot.bot.get_cached_user_info",
                return_value=make_mock_user_info("Alice", "alice@external.com"),
            ),
        ):
            event1 = {"user": "U111111111", "channel": governance_channel_id}
            await gov_bot.handle_member_joined_channel(mock_bot_server, event1)

        # Verify public message was posted for user 1
        messages_after_user1 = fake_client.get_channel_messages(governance_channel_id)
        assert len(messages_after_user1) == 1, "Should have posted public message for first user"

        # Verify KV store was updated to mark welcome as sent
        assert kv_storage.get(f"governance_welcome:channel:{governance_channel_id}") == "true"

        # STEP 2: User 2 joins (still no connections but welcome already sent) -> should get ephemeral
        with (
            patch(
                "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=True
            ),
            patch(
                "csbot.slackbot.channel_bot.bot.get_cached_user_info",
                return_value=make_mock_user_info("Bob", "bob@external.com"),
            ),
        ):
            event2 = {"user": "U222222222", "channel": governance_channel_id}
            await gov_bot.handle_member_joined_channel(mock_bot_server, event2)

        # Verify no additional public message was posted for user 2 (ephemeral only)
        messages_after_user2 = fake_client.get_channel_messages(governance_channel_id)
        assert len(messages_after_user2) == 1, (
            "Should not post another public message for second user (welcome already sent)"
        )

        # Verify ephemeral message was sent to user 2
        ephemeral_messages_user2 = fake_client.get_ephemeral_messages(user_id="U222222222")
        assert len(ephemeral_messages_user2) == 1, (
            "Should send ephemeral message to second user when welcome already sent"
        )

        # STEP 3: First dataset is added (simulate connection being added)
        regular_bot.profile.connections = {"bigquery_conn": Mock()}

        # STEP 4: User 3 joins (with connections now) -> should get ephemeral message only
        with (
            patch(
                "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=True
            ),
            patch(
                "csbot.slackbot.channel_bot.bot.get_cached_user_info",
                return_value=make_mock_user_info("Carol", "carol@external.com"),
            ),
        ):
            event3 = {"user": "U333333333", "channel": governance_channel_id}
            await gov_bot.handle_member_joined_channel(mock_bot_server, event3)

        # Verify no new public messages after user 3 (should be ephemeral)
        messages_after_user3 = fake_client.get_channel_messages(governance_channel_id)
        assert len(messages_after_user3) == len(messages_after_user2), (
            "Should not post public message for third user (connections exist)"
        )

        # Verify ephemeral message was sent to user 3
        ephemeral_messages_user3 = fake_client.get_ephemeral_messages(user_id="U333333333")
        assert len(ephemeral_messages_user3) == 1, (
            "Should send ephemeral message to third user when connections exist"
        )

        # Verify all ephemeral messages were sent
        assert len(fake_client.get_ephemeral_messages(user_id="U111111111")) == 0, (
            "User 1 should not have ephemeral (got pinned message)"
        )
        assert len(ephemeral_messages_user2) == 1, "User 2 should have ephemeral"
        assert len(ephemeral_messages_user3) == 1, "User 3 should have ephemeral"

    @pytest.mark.asyncio
    async def test_create_data_channel_and_multiple_members_join(self):
        """Test data channel creation with welcome message and multiple members joining.

        Scenario:
        1. Channel created with create_channel_and_bot_instance -> gets pinned welcome message
        2. User 1 joins data channel -> gets ephemeral welcome message
        3. User 2 joins data channel -> gets ephemeral welcome message
        4. User 3 joins data channel -> gets ephemeral welcome message

        The channel creation should post a pinned welcome message, then each user
        should get their own personalized ephemeral welcome message.
        """
        # Create FakeSlackClient
        fake_client = FakeSlackClient(token="xoxb-test-token")

        # Create three test users
        user1 = fake_client.create_test_user(name="Alice", email="alice@external.com", is_bot=False)
        user1["id"] = "U111111111"
        fake_client._users["U111111111"] = user1

        user2 = fake_client.create_test_user(name="Bob", email="bob@external.com", is_bot=False)
        user2["id"] = "U222222222"
        fake_client._users["U222222222"] = user2

        user3 = fake_client.create_test_user(name="Carol", email="carol@external.com", is_bot=False)
        user3["id"] = "U333333333"
        fake_client._users["U333333333"] = user3

        # Create governance bot for channel creation
        from csbot.slackbot.slack_utils import create_channel_and_bot_instance

        BotKey.from_channel_name(team_id="T123456789", channel_name="test-governance")
        governance_bot = Mock()
        governance_bot.client = fake_client
        governance_bot.kv_store = AsyncMock()
        governance_bot.kv_store.get_channel_id = AsyncMock(return_value=None)
        governance_bot.governance_alerts_channel = "test-governance"

        bot_server = Mock()
        bot_server.bot_manager = Mock()
        bot_server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()
        bot_server.channel_id_to_name = {}

        # Mock storage
        storage = AsyncMock()
        storage.create_bot_instance = AsyncMock()
        # Mock organization lookup for bot type determination
        mock_org = Mock()
        mock_org.organization_id = 123
        mock_org.has_governance_channel = True
        storage.list_organizations = AsyncMock(return_value=[mock_org])

        # Mock list_organizations for feature flag check
        mock_org = Mock()
        mock_org.organization_id = 123
        mock_org.has_governance_channel = False  # Combined bot model
        storage.list_organizations = AsyncMock(return_value=[mock_org])

        logger = Mock()

        # Create the channel in FakeSlackClient first so it exists for message posting
        channel_id = "C987654321"
        fake_client._channels[channel_id] = {
            "id": channel_id,
            "name": "test-data-channel",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": 1234567890,
            "creator": "U0000000000",
            "is_archived": False,
            "is_general": False,
            "members": [],
        }

        # Mock create_slack_client to return our FakeSlackClient
        def mock_create_slack_client(token: str):
            return fake_client

        # Mock post_slack_api for channel creation flow
        with (
            patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post_api,
            patch(
                "csbot.slackbot.slack_client.create_slack_client",
                side_effect=mock_create_slack_client,
            ),
        ):
            # Mock successful API responses
            mock_post_api.side_effect = [
                {"success": True, "channels": [], "channel_name_to_id": {}},  # get_all_channels
                {
                    "success": True,
                    "channel": {"id": channel_id, "name": "test-data-channel"},
                },  # Create channel
                {"success": True, "user_id": "B111111111"},  # Get dev tools bot user ID
                {"success": True, "user_id": "B222222222"},  # Get compass bot user ID
                {"success": True},  # Invite dev tools bot
                {"success": True},  # Invite compass bot
            ]

            # Mock the bot instance that will be retrieved after discovery
            regular_key = BotKey.from_channel_name(
                team_id="T123456789", channel_name="test-data-channel"
            )
            regular_bot = CompassChannelQANormalBotInstance.__new__(
                CompassChannelQANormalBotInstance
            )
            regular_bot.key = regular_key
            regular_bot.client = fake_client  # type: ignore[assignment]
            regular_bot.logger = Mock()
            regular_bot.profile = Mock()
            regular_bot.profile.connections = {"bigquery_conn": Mock()}
            regular_bot.associate_channel_id = AsyncMock()
            regular_bot.kv_store = AsyncMock()
            regular_bot.kv_store.get = AsyncMock(return_value=None)

            bot_server = Mock()
            bot_server.channel_id_to_name = {}
            bot_server.bots = {}
            bot_server.bots[regular_key] = regular_bot
            bot_server.bot_manager = Mock()
            bot_server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()
            bot_server.bot_manager.storage = AsyncMock()
            bot_server.bot_manager.storage.get_org_user_by_slack_user_id = AsyncMock(
                return_value=None
            )
            bot_server.bot_manager.storage.add_org_user = AsyncMock()

            # Set up bot config
            regular_bot.bot_config = Mock()
            regular_bot.bot_config.channel_name = "test-data-channel"
            regular_bot.bot_config.organization_id = 123
            regular_bot.bot_config.organization_name = "Test Org"
            regular_bot.bot_config.organization_type = BotInstanceType.STANDARD
            regular_bot.bot_config.is_prospector = False

            # Mock governance alerts channel to be THE SAME as data channel
            regular_bot.governance_alerts_channel = "test-data-channel"

            # Mock analytics store
            regular_bot.analytics_store = AsyncMock()

            # Mock additional methods needed by handle_member_joined_channel
            regular_bot.get_bot_user_id = AsyncMock(return_value="B987654321")
            regular_bot._log_analytics_event_with_context = AsyncMock()
            regular_bot._track_original_user_join_if_first_time = AsyncMock()
            regular_bot._process_member_join_incentive = AsyncMock()

            # Mock the answer_question_for_background_task method to generate different messages per user
            async def mock_answer_question_for_background_task(
                question: str, max_tokens: int, return_value_model
            ):
                from csbot.slackbot.channel_bot.bot import WelcomeMessageResult

                # Extract user ID from question to personalize message
                user_id = "unknown"
                if "U111111111" in question:
                    user_id = "Alice"
                elif "U222222222" in question:
                    user_id = "Bob"
                elif "U333333333" in question:
                    user_id = "Carol"

                return WelcomeMessageResult(
                    welcome_message=f"Welcome to Compass, {user_id}! Start asking data questions.",
                    follow_up_question="What insights are you looking for?",
                )

            regular_bot.answer_question_for_background_task = (
                mock_answer_question_for_background_task
            )

            # Create channel with bot instance
            result = await create_channel_and_bot_instance(
                bot_server=bot_server,
                channel_name="test-data-channel",
                user_id="U000000000",
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

            print(result)
            assert result["success"] is True
            channel_id = result["channel_id"]

            # Verify welcome message was posted and pinned
            channel_messages = fake_client.get_channel_messages(channel_id)
            assert len(channel_messages) >= 1, "Should have posted channel creation welcome message"
            pinned_items = await fake_client.pins_list(channel=channel_id)
            assert len(pinned_items["items"]) >= 1, "Should have pinned the welcome message"

            # Update regular_bot's kv_store to return the channel ID
            regular_bot.kv_store.get_channel_id = AsyncMock(return_value=channel_id)

        # STEP 2: User 1 joins -> should get ephemeral welcome
        with patch(
            "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=False
        ):
            event1 = {"user": "U111111111", "channel": channel_id}
            await regular_bot.handle_member_joined_channel(bot_server, event1)

        # Verify ephemeral message was sent to user 1
        ephemeral_messages_user1 = fake_client.get_ephemeral_messages(user_id="U111111111")
        assert len(ephemeral_messages_user1) == 1, "Should send ephemeral message to first user"
        assert "Welcome to Compass, Alice!" in ephemeral_messages_user1[0]["text"]

        # STEP 3: User 2 joins -> should get their own ephemeral welcome
        with patch(
            "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=False
        ):
            event2 = {"user": "U222222222", "channel": channel_id}
            await regular_bot.handle_member_joined_channel(bot_server, event2)

        # Verify ephemeral message was sent to user 2
        ephemeral_messages_user2 = fake_client.get_ephemeral_messages(user_id="U222222222")
        assert len(ephemeral_messages_user2) == 1, "Should send ephemeral message to second user"
        assert "Welcome to Compass, Bob!" in ephemeral_messages_user2[0]["text"]

        # STEP 4: User 3 joins -> should get their own ephemeral welcome
        with patch(
            "csbot.slackbot.channel_bot.bot.is_exempt_from_welcome_message", return_value=False
        ):
            event3 = {"user": "U333333333", "channel": channel_id}
            await regular_bot.handle_member_joined_channel(bot_server, event3)

        # Verify ephemeral message was sent to user 3
        ephemeral_messages_user3 = fake_client.get_ephemeral_messages(user_id="U333333333")
        assert len(ephemeral_messages_user3) == 1, "Should send ephemeral message to third user"
        assert "Welcome to Compass, Carol!" in ephemeral_messages_user3[0]["text"]

        # Verify exactly one public message (channel creation welcome) - member join messages are ephemeral
        channel_messages = fake_client.get_channel_messages(channel_id)
        assert len(channel_messages) == 2, (
            "Should have exactly 2 public message (channel creation welcome)"
        )

        # Verify all three users received their personalized ephemeral messages
        assert len(ephemeral_messages_user1) == 1, "User 1 should have 1 ephemeral message"
        assert len(ephemeral_messages_user2) == 1, "User 2 should have 1 ephemeral message"
        assert len(ephemeral_messages_user3) == 1, "User 3 should have 1 ephemeral message"

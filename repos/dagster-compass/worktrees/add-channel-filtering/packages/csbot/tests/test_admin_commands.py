import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from csbot.slackbot.admin_commands import AdminCommands
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import BotTypeGovernance, BotTypeQA
from csbot.slackbot.storage.onboarding_state import BotInstanceType

governance_channel_id = "C123456789"
main_channel_id = "CTest"


class TestAdminCommands:
    """Tests for admin commands functionality."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance for testing."""
        bot = Mock()
        bot.governance_alerts_channel = "governance-alerts"
        bot.kv_store = AsyncMock()
        bot.client = AsyncMock()
        bot.profile = Mock()
        bot.profile.connections = {"test_connection": Mock()}

        # Mock BotKey with proper to_bot_id method
        target_bot_key = BotKey.from_channel_name(team_id="T123456789", channel_name="test-channel")

        # Mock server_config for bot
        bot.server_config = Mock()
        bot.server_config.jwt_secret = Mock()
        bot.server_config.jwt_secret.get_secret_value.return_value = "test-secret"
        bot.server_config.public_url = "https://test.example.com"

        # Mock bot_server with proper config
        bot.bot_server = Mock()
        bot.bot_server.config = bot.server_config
        bot.bot_server.bot_manager = Mock()
        bot.bot_server.bot_manager.storage = AsyncMock()
        bot.bot_server.bot_manager.storage.get_connection_names_for_organization = AsyncMock(
            return_value=["test_connection"]
        )
        bot.bot_type = BotTypeGovernance(governed_bot_keys=set([target_bot_key]))
        governance_bot_key = BotKey.from_channel_name(
            team_id="T123456789", channel_name="test-channel-governance"
        )
        bot.key = governance_bot_key
        bot.bot_config = Mock()
        bot.bot_config.organization_id = 123  # Must be an int for JWT serialization
        bot.bot_config.team_id = "T123456789"  # Must be a string for JWT serialization
        bot.bot_config.organization_type = BotInstanceType.STANDARD  # Not prospector
        bot.bot_config.is_prospector = False  # Ensure admin commands work

        # Create a separate QA bot instance that will be discovered by _get_organization_bots()
        # This bot represents the governed data channel
        target_bot = Mock()
        target_bot.bot_type = BotTypeQA()
        target_bot.key = target_bot_key
        target_bot.profile = Mock()
        target_bot.profile.connections = {"test_connection": Mock()}
        target_bot.bot_config = Mock()
        target_bot.bot_config.organization_id = 123
        target_bot.bot_config.team_id = "T123456789"
        target_bot.kv_store = AsyncMock()

        bot.bot_server.bots = {target_bot_key: target_bot, governance_bot_key: bot}

        bot.local_context_store = Mock()
        bot.github_monitor = AsyncMock()
        bot.load_context_store = AsyncMock(return_value=Mock())

        async def mock_get_channel_id(channel_name: str) -> str:
            if channel_name == "governance-alerts":
                return governance_channel_id
            elif channel_name == "test-channel":
                return main_channel_id
            else:
                return f"C{hash(channel_name)}"

        bot.kv_store.get_channel_id = mock_get_channel_id

        return bot

    @pytest.fixture
    def admin_commands(self, mock_bot):
        """Create AdminCommands instance with mock bot."""
        return AdminCommands(mock_bot, mock_bot.bot_server)

    @pytest.mark.asyncio
    async def test_admin_init_command_in_governance_channel_success(self, admin_commands, mock_bot):
        """Test that !admin command works in governance channel."""
        # Create event in governance channel
        event = {"channel": governance_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        # Should return True (command handled)
        assert result is True

        # Should post ephemeral message with admin buttons
        mock_bot.client.chat_postEphemeral.assert_called_once()
        call_args = mock_bot.client.chat_postEphemeral.call_args
        assert call_args.kwargs["channel"] == governance_channel_id
        assert call_args.kwargs["user"] == "U123456789"
        assert call_args.kwargs["text"] == "Compass admin"
        assert "blocks" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_admin_init_command_in_wrong_channel_fails(self, admin_commands, mock_bot):
        """Test that !admin command fails in non-governance channel."""
        # Mock the governance channel ID lookup
        wrong_channel_id = "C987654321"

        # Create event in wrong channel
        event = {"channel": wrong_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        # Should return False (command not handled)
        assert result is False

        # Should NOT post any messages
        mock_bot.client.chat_postEphemeral.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_init_command_in_main_channel_fails(self, admin_commands, mock_bot):
        """Test that !admin command fails in non-governance channel."""
        # Create event in wrong channel
        event = {"channel": main_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        # Should return False (command not handled)
        assert result is False

        # Should NOT post any messages
        mock_bot.client.chat_postEphemeral.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_init_command_governance_channel_not_found(self, admin_commands, mock_bot):
        """Test !admin command when governance channel ID cannot be found."""

        event = {"channel": "C888", "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        # Should return False (command not handled)
        assert result is False

        # Should NOT post any messages
        mock_bot.client.chat_postEphemeral.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_init_command_shows_correct_buttons_with_connections(
        self, admin_commands, mock_bot
    ):
        """Test that admin command shows correct buttons when connections exist."""

        # Mock profile with connections
        mock_bot.profile.connections = {
            "bigquery_conn": Mock(),
            "postgres_conn": Mock(),
        }

        event = {"channel": governance_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        assert result is True

        # Check that the correct buttons are shown
        call_args = mock_bot.client.chat_postEphemeral.call_args
        blocks = call_args.kwargs["blocks"]

        # Should have two blocks: actions block and context block (help text)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "actions"
        assert blocks[1]["type"] == "context"

        # Should have 3 buttons: connection management, manage bots, billing
        elements = blocks[0]["elements"]
        assert len(elements) == 3

        # Check button texts
        button_texts = [elem["text"]["text"] for elem in elements]
        assert "🔗 Manage connections" in button_texts
        assert "🎛️ Manage channels" in button_texts
        assert "💳 Manage billing" in button_texts

    @pytest.mark.asyncio
    async def test_admin_init_command_with_connections_shows_management_buttons(
        self, admin_commands, mock_bot
    ):
        """Test that management buttons are shown when connections exist."""

        mock_bot.profile.connections = {
            "bigquery_conn": Mock(),
            "postgres_conn": Mock(),
        }

        event = {"channel": governance_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        assert result is True

        call_args = mock_bot.client.chat_postEphemeral.call_args
        blocks = call_args.kwargs["blocks"]
        elements = blocks[0]["elements"]
        button_texts = [elem["text"]["text"] for elem in elements]

        assert len(elements) == 3
        assert "🔗 Manage connections" in button_texts
        assert "🎛️ Manage channels" in button_texts
        assert "💳 Manage billing" in button_texts

        # Check help text in context block
        context_block = blocks[1]
        assert context_block["type"] == "context"
        assert len(context_block["elements"]) == 1
        help_text = context_block["elements"][0]["text"]
        assert "💡 *Need help?*" in help_text
        assert "Compass Docs" in help_text
        assert "https://docs.compass.dagster.io" in help_text

    @pytest.mark.asyncio
    async def test_admin_init_command_shows_get_started_button_without_connections(
        self, admin_commands, mock_bot
    ):
        """Test that admin command shows add warehouse button when no connections exist."""

        # Mock profile with no connections on both governance bot and QA bot
        mock_bot.profile.connections = {}
        # Also clear connections on the QA bot that _check_has_connections() checks
        target_bot_key = next(iter(mock_bot.bot_type.governed_bot_keys))
        mock_bot.bot_server.bots[target_bot_key].profile.connections = {}

        event = {"channel": governance_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        assert result is True

        # Check that the correct buttons are shown
        call_args = mock_bot.client.chat_postEphemeral.call_args
        blocks = call_args.kwargs["blocks"]

        # Should have two blocks: actions block and context block (help text)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "actions"
        assert blocks[1]["type"] == "context"

        # Should have only 1 button: add your warehouse
        elements = blocks[0]["elements"]
        assert len(elements) == 1

        # Check button text is "connect your data" variant
        button_text = elements[0]["text"]["text"]
        assert "🔗 Connect your data" == button_text

        # Check help text in context block
        context_block = blocks[1]
        assert context_block["type"] == "context"
        assert len(context_block["elements"]) == 1
        help_text = context_block["elements"][0]["text"]
        assert "💡 *Need help?*" in help_text
        assert "Compass Docs" in help_text
        assert "https://docs.compass.dagster.io" in help_text

    @pytest.mark.asyncio
    async def test_admin_init_command_prospector_org_shows_billing_only(
        self, admin_commands, mock_bot
    ):
        """Test that prospector organizations only see billing button."""
        from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME

        # Configure bot as prospector by setting up prospector connection
        mock_bot.bot_config.connections = {PROSPECTOR_CONNECTION_NAME: Mock()}
        mock_bot.bot_config.is_prospector = True  # Mock the property to return True

        event = {"channel": governance_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        assert result is True

        # Check that only billing button is shown
        call_args = mock_bot.client.chat_postEphemeral.call_args
        blocks = call_args.kwargs["blocks"]

        # Should have two blocks: actions block and context block
        assert len(blocks) == 2
        assert blocks[0]["type"] == "actions"
        assert blocks[1]["type"] == "context"

        # Should have only 1 button: billing
        elements = blocks[0]["elements"]
        assert len(elements) == 1

        # Check it's the billing button
        button_text = elements[0]["text"]["text"]
        assert "💳 Manage billing" == button_text

        # Check help text is present
        context_block = blocks[1]
        assert context_block["type"] == "context"
        help_text = context_block["elements"][0]["text"]
        assert "💡 *Need help?*" in help_text

    @pytest.mark.asyncio
    async def test_admin_init_command_with_empty_connections(self, admin_commands, mock_bot):
        """Test that admin command works correctly when profile has no connections."""

        # Mock profile with no connections
        mock_bot.profile.connections = {}

        event = {"channel": governance_channel_id, "user": "U123456789"}

        result = await admin_commands.handle_admin_init_command(event)

        # Should still work, just won't show dataset buttons
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_admin_interactive_wrong_channel_raises_error(self, admin_commands):
        """Test that interactive handler validates channel name from callback ID."""
        # Mock payload with callback ID from wrong channel
        payload = {
            "view": {"callback_id": "wrong-channel|add_dataset_form"},
            "type": "view_submission",
        }

        with pytest.raises(ValueError, match="Invalid channel name: wrong-channel"):
            await admin_commands.handle_admin_interactive(payload)

    @pytest.mark.asyncio
    async def test_handle_admin_interactive_show_add_dataset_modal(self, admin_commands, mock_bot):
        """Test showing add dataset modal through interactive handler."""
        # Mock payload for showing add dataset modal
        payload = {
            "actions": [
                {
                    "action_id": "show_managed_modal:foo",
                    "value": json.dumps(
                        {
                            "managed_modal_type": "add_or_update_dataset_modal",
                            "props": {
                                "available_connections": {"test_connection": ["test_channel"]}
                            },
                        }
                    ),
                }
            ],
            "trigger_id": "test_trigger_id",
            "channel": {"id": "C123"},
        }

        mock_bot.client.conversations_info.return_value = {"channel": {"name": "test_channel"}}
        mock_bot.client.views_open.return_value = {"view": {"id": "V123"}}
        result = await admin_commands.handle_admin_interactive(payload)

        assert result is True
        mock_bot.client.views_open.assert_called_once()

        # Verify modal structure
        call_args = mock_bot.client.views_open.call_args
        assert call_args.kwargs["trigger_id"] == "test_trigger_id"
        view = call_args.kwargs["view"]
        assert view["type"] == "modal"
        # Title is singular when showing loading state or connection selection
        assert view["title"]["text"] == "Add or Update Dataset"

    @pytest.mark.asyncio
    async def test_handle_admin_interactive_show_remove_dataset_modal(
        self, admin_commands, mock_bot
    ):
        """Test showing remove dataset modal through interactive handler."""

        payload = {
            "actions": [
                {
                    "action_id": "show_managed_modal:bar",
                    "value": json.dumps(
                        {
                            "managed_modal_type": "remove_dataset_modal",
                            "props": {
                                "available_connections": {"test_connection": ["test_channel"]},
                                "datasets_by_connection": {
                                    "test_connection": ["dataset1", "dataset2"]
                                },
                            },
                        }
                    ),
                }
            ],
            "trigger_id": "test_trigger_id",
            "channel": {"id": "C123"},
        }

        mock_bot.client.conversations_info.return_value = {"channel": {"name": "test_channel"}}
        mock_bot.client.views_open.return_value = {"view": {"id": "V123"}}

        result = await admin_commands.handle_admin_interactive(payload)

        assert result is True
        mock_bot.client.views_open.assert_called_once()

        call_args = mock_bot.client.views_open.call_args
        assert call_args.kwargs["trigger_id"] == "test_trigger_id"
        view = call_args.kwargs["view"]
        assert view["type"] == "modal"
        assert view["title"]["text"] == "Remove Datasets"

    @pytest.mark.asyncio
    async def test_process_remove_datasets_sends_success_notification(
        self, admin_commands, mock_bot
    ):
        """Test that _process_remove_datasets creates PR and sends custom message with View dataset update button."""

        with (
            patch("csbot.slackbot.admin_commands.remove_datasets_with_pr") as mock_remove,
            patch(
                "csbot.slackbot.admin_commands.SlackstreamMessage.post_message"
            ) as mock_post_message,
        ):
            pr_url = "https://github.com/test/repo/pull/789"
            mock_remove.return_value = pr_url

            mock_message = Mock()
            mock_message.message_ts = "123.456"
            mock_post_message.return_value = mock_message

            # Mock GitHub monitor and config
            mock_bot.github_monitor = AsyncMock()
            mock_bot.github_config = Mock()
            mock_bot.github_config.repo_name = "test/repo"
            mock_bot.load_context_store = AsyncMock(return_value=Mock())
            admin_commands.governance_bot = mock_bot

            await admin_commands._process_remove_datasets(
                connection="test_connection",
                datasets=["table1", "table2"],
                user_name="testuser",
                governance_channel_id="C123456789",
                preamble="Removing datasets",
            )

            mock_remove.assert_called_once()
            # Verify GitHub monitor was called to mark PR
            mock_bot.github_monitor.mark_pr.assert_called_once()
            # Verify custom success message was posted to Slack
            mock_bot.client.chat_postMessage.assert_called()

            # Check the message content includes the View dataset update button
            call_args = mock_bot.client.chat_postMessage.call_args
            assert call_args.kwargs["channel"] == "C123456789"
            assert call_args.kwargs["thread_ts"] == "123.456"
            assert "Dataset removal PR created" in call_args.kwargs["text"]

            # Check blocks include both text and button
            blocks = call_args.kwargs["blocks"]
            assert len(blocks) == 2
            assert blocks[0]["type"] == "section"
            assert blocks[1]["type"] == "actions"
            assert blocks[1]["elements"][0]["text"]["text"] == "View dataset update"

    @pytest.mark.asyncio
    async def test_process_remove_datasets_handles_errors(self, admin_commands):
        """Test that _process_remove_datasets reports errors when removal fails."""

        with (
            patch("csbot.slackbot.admin_commands.remove_datasets_with_pr") as mock_remove,
            patch("csbot.slackbot.admin_commands.notify_dataset_error") as mock_notify_error,
            patch(
                "csbot.slackbot.admin_commands.SlackstreamMessage.post_message"
            ) as mock_post_message,
        ):
            mock_remove.side_effect = ValueError("Removal failed")

            mock_message = Mock()
            mock_message.message_ts = "123.789"
            mock_post_message.return_value = mock_message

            await admin_commands._process_remove_datasets(
                connection="test_connection",
                datasets=["table1"],
                user_name="testuser",
                governance_channel_id="C123456789",
                preamble="Removing datasets",
            )

            mock_remove.assert_called_once()
            mock_notify_error.assert_called_once()

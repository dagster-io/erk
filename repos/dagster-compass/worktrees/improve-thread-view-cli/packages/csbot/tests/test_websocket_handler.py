"""Tests for WebSocket Slack event handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from slack_sdk.socket_mode.request import SocketModeRequest

from csbot.slackbot.event_handlers.websocket_handler import WebSocketSlackEventHandler
from csbot.slackbot.exceptions import BotUserFacingError, UserFacingError


class TestWebSocketSlackEventHandler:
    """Test cases for WebSocket Slack event handler."""

    @pytest.fixture
    def mock_server(self):
        """Mock CompassBotServer."""
        server = MagicMock()
        server.config.slack_app_token.get_secret_value.return_value = "test_token"
        server.logger = MagicMock()
        return server

    @pytest.fixture
    def mock_webserver(self):
        """Mock WebServer."""
        return MagicMock()

    @pytest.fixture
    def mock_bot(self):
        """Mock bot instance."""
        bot = MagicMock()
        bot.key.team_id = "T123456"
        bot.client = AsyncMock()
        bot.analytics_store = AsyncMock()
        bot.analytics_store.log_analytics_event = AsyncMock()
        bot.key.to_bot_id = MagicMock(return_value="test-bot-id")
        # Create a mock bot_config with specific return values
        mock_bot_config = MagicMock()
        # Use configure_mock to ensure the value is properly set
        mock_bot_config.configure_mock(organization_id="test-org-id")
        bot.bot_config = mock_bot_config
        return bot

    @pytest.fixture
    def handler(self, mock_server, mock_webserver, mock_bot):
        """Create WebSocketSlackEventHandler instance."""
        mock_server.bots = {"bot1": mock_bot}

        with patch("csbot.slackbot.event_handlers.websocket_handler.SocketModeClient"):
            return WebSocketSlackEventHandler(mock_server, mock_webserver)

    @pytest.mark.asyncio
    async def test_handle_user_facing_error_in_events_api(self, handler, mock_server, mock_bot):
        """Test that UserFacingError is properly handled and sent to Slack channel."""
        # Setup
        error_message = "Invalid cron job name"
        user_facing_error = UserFacingError(
            title="Invalid Input", message=error_message, error_type="user_input"
        )

        # Mock the server to raise UserFacingError
        mock_server.handle_event = AsyncMock(side_effect=user_facing_error)
        mock_server.bots = {"bot1": mock_bot}
        mock_bot.key.team_id = "T123456"

        # Mock bot to have channel access
        mock_bot.associated_channel_ids = {"C123456"}
        mock_server.get_bots_for_channel.return_value = [mock_bot]
        # Create a mock request for events_api
        mock_request = MagicMock(spec=SocketModeRequest)
        mock_request.type = "events_api"
        mock_request.envelope_id = "envelope_123"
        mock_request.payload = {
            "event": {
                "type": "app_mention",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "team_id": "T123456",
        }

        # Mock the socket client
        handler.slack_socket_client.send_socket_mode_response = AsyncMock()

        # Execute
        await handler.handle_events(None, mock_request)

        # Verify
        # 1. Should acknowledge the request
        handler.slack_socket_client.send_socket_mode_response.assert_called_once()

        # 2. Should call server.handle_event
        mock_server.handle_event.assert_called_once_with(
            {
                "type": "app_mention",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "app_mention",
            "T123456",
        )

        # 3. Should send error message to Slack channel
        mock_bot.client.chat_postMessage.assert_called_once_with(
            channel="C123456", text=error_message, thread_ts="1234567890.123456"
        )

    @pytest.mark.asyncio
    async def test_handle_user_facing_error_no_channel(self, handler, mock_server, mock_bot):
        """Test UserFacingError handling when no channel is found."""
        # Setup
        user_facing_error = UserFacingError(
            title="Test Error", message="Test message", error_type="user_input"
        )

        mock_server.handle_event = AsyncMock(side_effect=user_facing_error)
        mock_server.bots = {"bot1": mock_bot}

        # Create request with no channel
        mock_request = MagicMock(spec=SocketModeRequest)
        mock_request.type = "events_api"
        mock_request.envelope_id = "envelope_123"
        mock_request.payload = {
            "event": {
                "type": "app_mention",
                # No channel field
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "team_id": "T123456",
        }

        handler.slack_socket_client.send_socket_mode_response = AsyncMock()

        # Execute
        await handler.handle_events(None, mock_request)

        # Verify - should not send message and should log warning
        mock_bot.client.chat_postMessage.assert_not_called()
        mock_server.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_handle_user_facing_error_no_bot_for_team(self, handler, mock_server, mock_bot):
        """Test UserFacingError handling when no bot is found for the team."""
        # Setup
        user_facing_error = UserFacingError(
            title="Test Error", message="Test message", error_type="user_input"
        )

        mock_server.handle_event = AsyncMock(side_effect=user_facing_error)
        # Bot has different team ID
        mock_bot.key.team_id = "T999999"
        mock_server.bots = {"bot1": mock_bot}

        # Mock bot to have NO channel access for C123456
        mock_bot.associated_channel_ids = {"C999999"}  # Different channel
        mock_server.get_bots_for_channel.return_value = []  # No bots found
        # Create request for different team
        mock_request = MagicMock(spec=SocketModeRequest)
        mock_request.type = "events_api"
        mock_request.envelope_id = "envelope_123"
        mock_request.payload = {
            "event": {
                "type": "app_mention",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "team_id": "T123456",  # Different from bot's team
        }

        handler.slack_socket_client.send_socket_mode_response = AsyncMock()

        # Execute
        await handler.handle_events(None, mock_request)

        # Verify - should not send message and should log warning
        mock_bot.client.chat_postMessage.assert_not_called()
        mock_server.logger.warning.assert_called_with(
            "No bot found for channel C123456, cannot send UserFacingError to user"
        )

    @pytest.mark.asyncio
    async def test_handle_user_facing_error_thread_reply(self, handler, mock_server, mock_bot):
        """Test UserFacingError handling in thread reply context."""
        # Setup
        error_message = "Invalid command"
        user_facing_error = UserFacingError(
            title="Invalid Input", message=error_message, error_type="user_input"
        )

        mock_server.handle_event = AsyncMock(side_effect=user_facing_error)
        mock_server.bots = {"bot1": mock_bot}
        mock_bot.key.team_id = "T123456"

        # Mock bot to have channel access
        mock_bot.associated_channel_ids = {"C123456"}
        mock_server.get_bots_for_channel.return_value = [mock_bot]
        # Create request with thread_ts
        mock_request = MagicMock(spec=SocketModeRequest)
        mock_request.type = "events_api"
        mock_request.envelope_id = "envelope_123"
        mock_request.payload = {
            "event": {
                "type": "message",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "thread_ts": "1234567890.000000",  # Thread reply
                "user": "U123456",
                "text": "test message",
            },
            "team_id": "T123456",
        }

        handler.slack_socket_client.send_socket_mode_response = AsyncMock()

        # Execute
        await handler.handle_events(None, mock_request)

        # Verify - should use thread_ts for the reply
        mock_bot.client.chat_postMessage.assert_called_once_with(
            channel="C123456",
            text=error_message,
            thread_ts="1234567890.000000",  # Should use thread_ts, not event ts
        )

    @pytest.mark.asyncio
    async def test_regular_exception_handling_not_affected(self, handler, mock_server, mock_bot):
        """Test that regular exceptions are still handled normally (not as UserFacingError)."""
        # Setup
        regular_error = ValueError("Some internal error")

        mock_server.handle_event = AsyncMock(side_effect=regular_error)
        mock_server.bots = {"bot1": mock_bot}

        # Create request
        mock_request = MagicMock(spec=SocketModeRequest)
        mock_request.type = "events_api"
        mock_request.envelope_id = "envelope_123"
        mock_request.payload = {
            "event": {
                "type": "app_mention",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "team_id": "T123456",
        }

        handler.slack_socket_client.send_socket_mode_response = AsyncMock()

        # Execute
        await handler.handle_events(None, mock_request)

        # Verify
        # 1. Should still acknowledge the request
        handler.slack_socket_client.send_socket_mode_response.assert_called_once()

        # 2. Should call server.handle_event
        mock_server.handle_event.assert_called_once()

        # 3. Should NOT send message to Slack (only logs error)
        mock_bot.client.chat_postMessage.assert_not_called()

        # 4. Should log the error
        mock_server.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_bot_user_facing_error_special_path(self, handler, mock_server, mock_bot):
        """Test that BotUserFacingError uses its source_bot directly without channel lookup."""
        # Setup
        error_message = "Bot-specific error message"
        bot_user_facing_error = BotUserFacingError(
            source_bot=mock_bot, title="Bot Error", message=error_message, error_type="bot_error"
        )

        # Mock the server to raise BotUserFacingError
        mock_server.handle_event = AsyncMock(side_effect=bot_user_facing_error)

        # Create a mock request for events_api
        mock_request = MagicMock(spec=SocketModeRequest)
        mock_request.type = "events_api"
        mock_request.envelope_id = "envelope_123"
        mock_request.payload = {
            "event": {
                "type": "app_mention",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "team_id": "T123456",
        }

        # Mock the socket client
        handler.slack_socket_client.send_socket_mode_response = AsyncMock()

        # Execute
        await handler.handle_events(None, mock_request)

        # Verify
        # 1. Should acknowledge the request
        handler.slack_socket_client.send_socket_mode_response.assert_called_once()

        # 2. Should call server.handle_event
        mock_server.handle_event.assert_called_once_with(
            {
                "type": "app_mention",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "user": "U123456",
                "text": "test message",
            },
            "app_mention",
            "T123456",
        )

        # 3. Should send error message using source_bot directly (no channel lookup needed)
        mock_bot.client.chat_postMessage.assert_called_once_with(
            channel="C123456", text=error_message, thread_ts="1234567890.123456"
        )

        # 4. Should NOT call get_bots_for_channel since BotUserFacingError has source_bot
        mock_server.get_bots_for_channel.assert_not_called()

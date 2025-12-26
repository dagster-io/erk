"""Tests for error scenarios and exception handling."""

from unittest.mock import patch

import pytest
from anthropic.types import (
    Message,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    Usage,
)
from anthropic.types.message_delta_usage import MessageDeltaUsage
from anthropic.types.raw_message_delta_event import Delta

from csbot.agents.messages import AgentTextMessage
from csbot.slackbot.exceptions import UserFacingError


class TestStreamingErrors:
    """Test error scenarios during streaming."""

    @pytest.mark.asyncio
    async def test_stream_messages_max_tokens_error(self, agent, mock_anthropic_client):
        """Test that max_tokens error is properly handled."""

        async def mock_stream():
            # Message start
            yield RawMessageStartEvent(
                type="message_start",
                message=Message(
                    id="msg_123",
                    content=[],
                    model="claude-3-sonnet-20240229",
                    role="assistant",
                    stop_reason=None,
                    stop_sequence=None,
                    type="message",
                    usage=Usage(input_tokens=10, output_tokens=0),
                ),
            )

            # Message delta with max_tokens
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="max_tokens", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=1000),
            )

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            with pytest.raises(UserFacingError, match="Query used too many tokens"):
                async for _ in agent.stream_messages_with_tools(
                    model="claude-3-sonnet-20240229",
                    system="You are a helpful assistant.",
                    messages=[
                        AgentTextMessage(role="user", content="Generate a very long response")
                    ],
                    tools={},
                    max_tokens=1000,
                ):
                    pass


class TestUserFacingError:
    """Test UserFacingError exception behavior."""

    def test_user_facing_error(self):
        """Test UserFacingError exception."""
        error = UserFacingError(title="Test Title", message="Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.title == "Test Title"

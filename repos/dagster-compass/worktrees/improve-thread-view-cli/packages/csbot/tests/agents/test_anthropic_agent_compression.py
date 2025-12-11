"""Tests for mid-execution history compression in stream_messages_with_tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import (
    Message,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockStopEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    TextBlock,
    Usage,
)
from anthropic.types.message_delta_usage import MessageDeltaUsage
from anthropic.types.raw_message_delta_event import Delta
from anthropic.types.text_delta import TextDelta

from csbot.agents.anthropic.anthropic_agent import AnthropicAgent
from csbot.agents.compression import (
    compress_history,
    estimate_tokens_for_history,
    estimate_tokens_for_message,
    is_context_window_exceeded_exception,
)
from csbot.agents.messages import (
    AgentModelSpecificMessage,
    AgentTextMessage,
)
from csbot.agents.protocol import AgentCompressionConfig


class TestEstimateTokens:
    """Test token estimation functions."""

    def test_estimate_tokens_text_message(self):
        """Test token estimation for a simple text message."""
        message = AgentTextMessage(role="user", content="Hello world!")
        tokens = estimate_tokens_for_message(message)
        # ~12 chars / 4 + 1 = 4
        assert tokens == 4

    def test_estimate_tokens_model_specific_message_str(self):
        """Test token estimation for model-specific message with string content."""
        message = AgentModelSpecificMessage(role="assistant", content="This is a response")
        tokens = estimate_tokens_for_message(message)
        # ~18 chars / 4 + 1 = 5
        assert tokens == 5

    def test_estimate_tokens_model_specific_message_list(self):
        """Test token estimation for model-specific message with list content."""
        message = AgentModelSpecificMessage(
            role="user",
            content=[
                {"type": "text", "text": "Hello"},
                {"type": "tool_result", "content": "Result data"},
            ],
        )
        tokens = estimate_tokens_for_message(message)
        assert tokens > 0  # Should have a reasonable estimate

    def test_estimate_tokens_history(self):
        """Test token estimation for a conversation history."""
        history = [
            AgentTextMessage(role="user", content="Hello"),
            AgentModelSpecificMessage(role="assistant", content="Hi there!"),
            AgentTextMessage(role="user", content="How are you?"),
        ]
        tokens = estimate_tokens_for_history(history)
        assert tokens > 0


class TestIsContextWindowExceededException:
    """Test context window exceeded exception detection."""

    def test_detects_input_too_long(self):
        """Test detection of 'input is too long' error."""
        exc = Exception("Error: Input is too long for the model")
        assert is_context_window_exceeded_exception(exc) is True

    def test_detects_context_length_exceeded(self):
        """Test detection of context_length_exceeded error."""
        exc = Exception("context_length_exceeded: maximum tokens exceeded")
        assert is_context_window_exceeded_exception(exc) is True

    def test_detects_maximum_context_length(self):
        """Test detection of 'maximum context length' error."""
        exc = Exception("maximum context length is 200000 tokens")
        assert is_context_window_exceeded_exception(exc) is True

    def test_does_not_match_other_errors(self):
        """Test that unrelated errors are not flagged."""
        exc = Exception("API rate limit exceeded")
        assert is_context_window_exceeded_exception(exc) is False


class TestCompressHistory:
    """Test history compression function."""

    @pytest.mark.asyncio
    async def test_compress_history_short_history(self):
        """Test that short history is returned unchanged."""
        history = [
            AgentTextMessage(role="user", content="Hello"),
            AgentTextMessage(role="assistant", content="Hi"),
        ]
        mock_agent = MagicMock()

        result = await compress_history(history, 1000, mock_agent)
        assert result == history
        mock_agent.create_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_history_success(self):
        """Test successful history compression."""
        # Create history with enough messages to compress
        history = [
            AgentTextMessage(role="user", content="Original question"),
            AgentModelSpecificMessage(
                role="assistant",
                content=[{"type": "text", "text": "First response with lots of detail"}],
            ),
            AgentModelSpecificMessage(
                role="user",
                content=[{"type": "tool_result", "content": "Tool output data"}],
            ),
            AgentModelSpecificMessage(
                role="assistant",
                content=[{"type": "text", "text": "Second response"}],
            ),
            AgentTextMessage(role="user", content="Follow up question"),
            AgentTextMessage(role="assistant", content="Final response"),
        ]

        mock_agent = MagicMock()
        mock_agent.model = "test-model"
        mock_agent.create_completion = AsyncMock(
            return_value="Summary: The conversation discussed the original question."
        )

        result = await compress_history(history, 1000, mock_agent)

        # Should have compressed middle messages
        assert len(result) < len(history)
        # First message (original request) should be preserved
        assert result[0] == history[0]
        # Last messages should be preserved
        assert result[-1] == history[-1]
        mock_agent.create_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_history_failure_returns_original(self):
        """Test that compression failure returns original history."""
        history = [
            AgentTextMessage(role="user", content="Question 1"),
            AgentTextMessage(role="assistant", content="Answer 1"),
            AgentTextMessage(role="user", content="Question 2"),
            AgentTextMessage(role="assistant", content="Answer 2"),
            AgentTextMessage(role="user", content="Question 3"),
            AgentTextMessage(role="assistant", content="Answer 3"),
        ]

        mock_agent = MagicMock()
        mock_agent.model = "test-model"
        mock_agent.create_completion = AsyncMock(side_effect=Exception("API error"))

        result = await compress_history(history, 1000, mock_agent)

        # Should return original history on failure
        assert result == history


class TestCompressionTriggeredProactively:
    """Test proactive compression in stream_messages_with_tools."""

    @pytest.mark.asyncio
    async def test_compression_triggered_proactively(self):
        """Test that compression is triggered when history exceeds threshold."""
        agent = AnthropicAgent.from_api_key("test-api-key")

        # Create a compression agent mock
        compression_agent = MagicMock()
        compression_agent.model = "test-model"
        compression_agent.create_completion = AsyncMock(
            return_value="Summary of conversation"
        )

        compression_config = AgentCompressionConfig(
            compression_agent=compression_agent,
            threshold_tokens=10,  # Very low threshold to trigger compression
            target_tokens=5,
        )

        # Create large history that exceeds threshold
        large_messages = [
            AgentTextMessage(role="user", content="A" * 100),  # ~25 tokens
        ]

        # Mock the Anthropic client to return a simple response
        async def mock_stream():
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
            yield RawContentBlockStartEvent(
                type="content_block_start",
                index=0,
                content_block=TextBlock(type="text", text=""),
            )
            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=TextDelta(type="text_delta", text="Hello"),
            )
            yield RawContentBlockStopEvent(type="content_block_stop", index=0)
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="end_turn", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=1),
            )

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_client):
            with patch(
                "csbot.agents.anthropic.anthropic_agent.compress_history",
                new_callable=AsyncMock,
            ) as mock_compress:
                mock_compress.return_value = large_messages  # Return same for simplicity

                events = []
                async for event in agent.stream_messages_with_tools(
                    model="claude-3-sonnet-20240229",
                    system="You are helpful.",
                    messages=large_messages,
                    tools={},
                    max_tokens=100,
                    compression_config=compression_config,
                ):
                    events.append(event)

                # Compression should have been called
                mock_compress.assert_called_once()


class TestCompressionTriggeredReactively:
    """Test reactive compression when API returns context exceeded error."""

    @pytest.mark.asyncio
    async def test_compression_triggered_reactively(self):
        """Test that compression is triggered on context window exceeded error."""
        agent = AnthropicAgent.from_api_key("test-api-key")

        compression_agent = MagicMock()
        compression_agent.model = "test-model"
        compression_agent.create_completion = AsyncMock(
            return_value="Summary of conversation"
        )

        compression_config = AgentCompressionConfig(
            compression_agent=compression_agent,
            threshold_tokens=1_000_000,  # High threshold - won't trigger proactively
            target_tokens=1000,
        )

        messages = [
            AgentTextMessage(role="user", content="Hello"),
        ]

        # First call raises context exceeded, second succeeds
        call_count = 0

        async def mock_create_with_retry(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Input is too long for the model context window")

            # Return a stream on second call
            async def mock_stream():
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
                yield RawContentBlockStartEvent(
                    type="content_block_start",
                    index=0,
                    content_block=TextBlock(type="text", text=""),
                )
                yield RawContentBlockDeltaEvent(
                    type="content_block_delta",
                    index=0,
                    delta=TextDelta(type="text_delta", text="Response"),
                )
                yield RawContentBlockStopEvent(type="content_block_stop", index=0)
                yield RawMessageDeltaEvent(
                    type="message_delta",
                    delta=Delta(stop_reason="end_turn", stop_sequence=None),
                    usage=MessageDeltaUsage(output_tokens=1),
                )

            return mock_stream()

        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = mock_create_with_retry

        with patch.object(agent, "client", mock_client):
            with patch(
                "csbot.agents.anthropic.anthropic_agent.compress_history",
                new_callable=AsyncMock,
            ) as mock_compress:
                mock_compress.return_value = messages

                events = []
                async for event in agent.stream_messages_with_tools(
                    model="claude-3-sonnet-20240229",
                    system="You are helpful.",
                    messages=messages,
                    tools={},
                    max_tokens=100,
                    compression_config=compression_config,
                ):
                    events.append(event)

                # Compression should have been called for retry
                mock_compress.assert_called_once()
                # API should have been called twice
                assert call_count == 2


class TestNoCompressionBelowThreshold:
    """Test that compression is not triggered when history is small."""

    @pytest.mark.asyncio
    async def test_no_compression_below_threshold(self):
        """Test that compression is not triggered when history is below threshold."""
        agent = AnthropicAgent.from_api_key("test-api-key")

        compression_agent = MagicMock()
        compression_agent.model = "test-model"

        compression_config = AgentCompressionConfig(
            compression_agent=compression_agent,
            threshold_tokens=1_000_000,  # Very high threshold
            target_tokens=100_000,
        )

        messages = [
            AgentTextMessage(role="user", content="Hello"),  # ~2 tokens
        ]

        async def mock_stream():
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
            yield RawContentBlockStartEvent(
                type="content_block_start",
                index=0,
                content_block=TextBlock(type="text", text=""),
            )
            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=TextDelta(type="text_delta", text="Hi"),
            )
            yield RawContentBlockStopEvent(type="content_block_stop", index=0)
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="end_turn", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=1),
            )

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_client):
            with patch(
                "csbot.agents.anthropic.anthropic_agent.compress_history",
                new_callable=AsyncMock,
            ) as mock_compress:
                events = []
                async for event in agent.stream_messages_with_tools(
                    model="claude-3-sonnet-20240229",
                    system="You are helpful.",
                    messages=messages,
                    tools={},
                    max_tokens=100,
                    compression_config=compression_config,
                ):
                    events.append(event)

                # Compression should NOT have been called
                mock_compress.assert_not_called()


class TestCompressionConfigNone:
    """Test normal behavior when compression config is None."""

    @pytest.mark.asyncio
    async def test_compression_config_none(self):
        """Test that agent works normally when compression config is None."""
        agent = AnthropicAgent.from_api_key("test-api-key")

        messages = [
            AgentTextMessage(role="user", content="Hello"),
        ]

        async def mock_stream():
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
            yield RawContentBlockStartEvent(
                type="content_block_start",
                index=0,
                content_block=TextBlock(type="text", text=""),
            )
            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=TextDelta(type="text_delta", text="Hello!"),
            )
            yield RawContentBlockStopEvent(type="content_block_stop", index=0)
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="end_turn", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=1),
            )

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_client):
            events = []
            async for event in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are helpful.",
                messages=messages,
                tools={},
                max_tokens=100,
                compression_config=None,  # Explicitly None
            ):
                events.append(event)

            # Should have received events normally
            assert len(events) > 0


class TestCompressionFailureAllowsRetry:
    """Test graceful handling when compression fails."""

    @pytest.mark.asyncio
    async def test_compression_failure_allows_retry(self):
        """Test that when compression fails, original history is used and retry succeeds."""
        agent = AnthropicAgent.from_api_key("test-api-key")

        compression_agent = MagicMock()
        compression_agent.model = "test-model"
        # Compression fails
        compression_agent.create_completion = AsyncMock(side_effect=Exception("Compression failed"))

        compression_config = AgentCompressionConfig(
            compression_agent=compression_agent,
            threshold_tokens=10,  # Low threshold to trigger compression
            target_tokens=5,
        )

        messages = [
            AgentTextMessage(role="user", content="A" * 100),  # Exceeds threshold
        ]

        async def mock_stream():
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
            yield RawContentBlockStartEvent(
                type="content_block_start",
                index=0,
                content_block=TextBlock(type="text", text=""),
            )
            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=TextDelta(type="text_delta", text="Response"),
            )
            yield RawContentBlockStopEvent(type="content_block_stop", index=0)
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="end_turn", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=1),
            )

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_client):
            # Should not raise - compression failure is gracefully handled
            events = []
            async for event in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are helpful.",
                messages=messages,
                tools={},
                max_tokens=100,
                compression_config=compression_config,
            ):
                events.append(event)

            # Should have received events (compression failed but original history worked)
            assert len(events) > 0

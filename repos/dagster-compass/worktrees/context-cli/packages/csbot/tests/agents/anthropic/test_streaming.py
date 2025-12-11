"""Tests for streaming functionality including text, tools, and callbacks."""

import asyncio
from unittest.mock import patch

import pytest
from anthropic.types import (
    Message,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockStopEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextBlock,
    ToolUseBlock,
    Usage,
)
from anthropic.types.input_json_delta import InputJSONDelta
from anthropic.types.message_delta_usage import MessageDeltaUsage
from anthropic.types.raw_message_delta_event import Delta
from anthropic.types.text_delta import TextDelta

from csbot.agents.messages import (
    AgentInputJSONDelta,
    AgentTextBlock,
    AgentTextDelta,
    AgentTextMessage,
    AgentToolUseBlock,
)


class TestStreamingText:
    """Test text streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_messages_simple_text(self, agent, mock_anthropic_client):
        """Test streaming messages with simple text response."""

        # Create mock stream events
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

            # Content block start
            yield RawContentBlockStartEvent(
                type="content_block_start",
                index=0,
                content_block=TextBlock(type="text", text=""),
            )

            # Content block delta
            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=TextDelta(type="text_delta", text="Hello!"),
            )

            # Content block stop
            yield RawContentBlockStopEvent(type="content_block_stop", index=0)

            # Message delta with end
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="end_turn", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=5),
            )

            # Message stop
            yield RawMessageStopEvent(type="message_stop")

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            events = []
            async for event in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Hello!")],
                tools={},
                max_tokens=1000,
            ):
                events.append(event)

        # Verify we got the expected events
        assert len(events) == 3  # start, delta, stop
        assert events[0].type == "start"
        assert isinstance(events[0].content_block, AgentTextBlock)
        assert events[1].type == "delta"
        assert isinstance(events[1].delta, AgentTextDelta)
        assert events[1].delta.text == "Hello!"
        assert events[2].type == "stop"


class TestStreamingTools:
    """Test tool use streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_messages_with_tool_use(self, agent, mock_anthropic_client):
        """Test streaming messages with tool use."""

        # Create a simple tool
        def test_tool(query: str) -> str:
            return f"Tool result for: {query}"

        tools = {"test_tool": test_tool}

        # Create mock stream events for tool use
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

            # Tool use content block start
            yield RawContentBlockStartEvent(
                type="content_block_start",
                index=0,
                content_block=ToolUseBlock(
                    id="toolu_123",
                    type="tool_use",
                    name="test_tool",
                    input={},
                ),
            )

            # Tool use input delta
            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=InputJSONDelta(type="input_json_delta", partial_json='{"query": "test"}'),
            )

            # Content block stop
            yield RawContentBlockStopEvent(type="content_block_stop", index=0)

            # Message delta
            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="tool_use", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=15),
            )

            # Message stop
            yield RawMessageStopEvent(type="message_stop")

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            events = []
            async for event in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Use the test tool")],
                tools=tools,
                max_tokens=1000,
            ):
                events.append(event)

        # Verify we got the expected events
        assert len(events) >= 3  # start, delta, stop (plus potential follow-up)
        assert events[0].type == "start"
        assert isinstance(events[0].content_block, AgentToolUseBlock)
        assert events[0].content_block.name == "test_tool"
        assert events[1].type == "delta"
        assert isinstance(events[1].delta, AgentInputJSONDelta)
        assert events[2].type == "stop"

    @pytest.mark.asyncio
    async def test_stream_messages_with_async_tool(self, agent, mock_anthropic_client):
        """Test streaming messages with async tool."""

        async def async_tool(query: str) -> str:
            await asyncio.sleep(0.01)  # Simulate async operation
            return f"Async result for: {query}"

        tools = {"async_tool": async_tool}

        # Mock a simple tool use scenario
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
                content_block=ToolUseBlock(
                    id="toolu_456",
                    type="tool_use",
                    name="async_tool",
                    input={},
                ),
            )

            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=InputJSONDelta(
                    type="input_json_delta", partial_json='{"query": "async_test"}'
                ),
            )

            yield RawContentBlockStopEvent(type="content_block_stop", index=0)

            yield RawMessageDeltaEvent(
                type="message_delta",
                delta=Delta(stop_reason="tool_use", stop_sequence=None),
                usage=MessageDeltaUsage(output_tokens=15),
            )

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            events = []
            async for event in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Use async tool")],
                tools=tools,
                max_tokens=1000,
            ):
                events.append(event)

        # Verify the async tool was handled properly
        assert len(events) >= 3
        assert events[0].type == "start"
        assert isinstance(events[0].content_block, AgentToolUseBlock)
        assert events[0].content_block.name == "async_tool"

    @pytest.mark.asyncio
    async def test_stream_messages_tool_error(self, agent, mock_anthropic_client):
        """Test that tool errors are properly handled."""

        def error_tool(query: str) -> str:
            raise ValueError("Tool execution failed")

        tools = {"error_tool": error_tool}

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
                content_block=ToolUseBlock(
                    id="toolu_error",
                    type="tool_use",
                    name="error_tool",
                    input={},
                ),
            )

            yield RawContentBlockDeltaEvent(
                type="content_block_delta",
                index=0,
                delta=InputJSONDelta(type="input_json_delta", partial_json='{"query": "test"}'),
            )

            yield RawContentBlockStopEvent(type="content_block_stop", index=0)

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            events = []
            # This should not raise an exception - tool errors should be handled gracefully
            async for event in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Use error tool")],
                tools=tools,
                max_tokens=1000,
            ):
                events.append(event)

        assert len(events) >= 3


class TestStreamingCallbacks:
    """Test callback functionality during streaming."""

    @pytest.mark.asyncio
    async def test_stream_messages_with_history_callback(self, agent, mock_anthropic_client):
        """Test streaming with history callback."""
        history_events = []

        async def on_history_added(message):
            history_events.append(message)

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
                delta=TextDelta(type="text_delta", text="Test response"),
            )

            yield RawContentBlockStopEvent(type="content_block_stop", index=0)

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            async for _ in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Hello")],
                tools={},
                max_tokens=1000,
                on_history_added=on_history_added,
            ):
                pass

        # Verify history callback was called
        assert len(history_events) == 1
        assert history_events[0].role == "assistant"
        assert history_events[0].content == "Test response"

    @pytest.mark.asyncio
    async def test_stream_messages_with_token_usage_callback(self, agent, mock_anthropic_client):
        """Test streaming with token usage callback."""
        token_usage_events = []

        async def on_token_usage(total_tokens, token_breakdown):
            token_usage_events.append((total_tokens, token_breakdown))

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
                # Anthropic reports cumulative totals, so input_tokens appears in both events
                usage=MessageDeltaUsage(input_tokens=10, output_tokens=5),
            )

        mock_anthropic_client.messages.create.return_value = mock_stream()

        with patch.object(agent, "client", mock_anthropic_client):
            async for _ in agent.stream_messages_with_tools(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Hello")],
                tools={},
                max_tokens=1000,
                on_token_usage=on_token_usage,
            ):
                pass

        # Verify token usage callback was called
        assert len(token_usage_events) == 1
        total_tokens, token_breakdown = token_usage_events[0]
        assert total_tokens == 15  # 10 + 5
        assert token_breakdown["input_tokens"] == 10
        assert token_breakdown["output_tokens"] == 5
        assert token_breakdown["total_tokens"] == 15

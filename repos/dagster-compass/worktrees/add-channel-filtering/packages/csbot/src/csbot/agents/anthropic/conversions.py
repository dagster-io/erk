"""Conversion functions between Anthropic types and Agent types."""

import re
from collections.abc import Callable
from copy import deepcopy

from anthropic.types import (
    ContentBlock,
    MessageParam,
    RawContentBlockDelta,
    RawMessageStreamEvent,
    ToolParam,
)

from csbot.agents.messages import (
    AgentBlockDelta,
    AgentBlockDeltaEvent,
    AgentBlockEvent,
    AgentContentBlock,
    AgentInputJSONDelta,
    AgentMessage,
    AgentModelSpecificMessage,
    AgentStartBlockEvent,
    AgentStopBlockEvent,
    AgentTextBlock,
    AgentTextDelta,
    AgentTextMessage,
    AgentToolUseBlock,
)
from csbot.agents.tool_schema import build_input_schema_from_function


def anthropic_content_block_delta_to_agent(
    delta: RawContentBlockDelta,
) -> AgentBlockDelta:
    """Convert Anthropic content block delta to Agent delta."""
    if delta.type == "text_delta":
        return AgentTextDelta(type="text_delta", text=delta.text)
    elif delta.type == "input_json_delta":
        return AgentInputJSONDelta(type="input_json_delta", partial_json=delta.partial_json)
    else:
        raise ValueError(f"Unknown delta type: {delta.type}")


def anthropic_content_block_to_agent(
    content_block: ContentBlock,
) -> AgentContentBlock:
    """Convert Anthropic content block to Agent content block."""
    if content_block.type == "tool_use":
        return AgentToolUseBlock(
            type="call_tool",
            id=content_block.id,
            name=content_block.name,
        )
    elif content_block.type == "text":
        return AgentTextBlock(type="output_text")
    else:
        raise ValueError(f"Unknown content block type: {content_block.type}")


def anthropic_message_param_to_agent(
    message: MessageParam,
) -> AgentModelSpecificMessage:
    """Convert Anthropic message param to Agent message."""
    return AgentModelSpecificMessage(role=message["role"], content=message["content"])


def agent_to_anthropic_message_param(
    message: AgentMessage,
) -> MessageParam:
    """Convert Agent message to Anthropic message param."""
    if isinstance(message, AgentModelSpecificMessage):
        return MessageParam(role=message.role, content=message.content)
    elif isinstance(message, AgentTextMessage):
        return MessageParam(role=message.role, content=message.content)
    else:
        raise ValueError(f"Message is not an AgentMessage: {message}")


def anthropic_raw_message_stream_event_to_agent(
    event: RawMessageStreamEvent,
) -> AgentBlockEvent | None:
    """Convert Anthropic stream event to Agent event."""
    if event.type == "content_block_start":
        return AgentStartBlockEvent(
            type="start",
            index=event.index,
            content_block=anthropic_content_block_to_agent(event.content_block),
        )
    elif event.type == "content_block_stop":
        return AgentStopBlockEvent(type="stop", index=event.index)
    elif event.type == "content_block_delta":
        return AgentBlockDeltaEvent(
            type="delta",
            index=event.index,
            delta=anthropic_content_block_delta_to_agent(event.delta),
        )
    else:
        return None


def create_anthropic_tool_param(name: str, tool_func: Callable[..., object]) -> ToolParam:
    """
    Create an Anthropic tool parameter definition from a Python function using Pydantic.

    Args:
        name: Name of the tool
        tool_func: The function to create a tool definition for

    Returns:
        ToolParam containing the tool definition for Anthropic's API
    """
    # Get docstring for description
    doc = tool_func.__doc__ or f"Tool: {name}"

    # Build input schema using shared utility
    input_schema = build_input_schema_from_function(tool_func)

    # Create the tool definition
    tool_def: ToolParam = {
        "name": name,
        "description": doc,
        "input_schema": input_schema,
    }

    return tool_def


def prepare_messages_with_cache_control(messages: list[AgentMessage]) -> list[AgentMessage]:
    """Prepare messages with cache control for Anthropic API."""
    messages_with_cache_control = deepcopy(messages)
    for message in reversed(messages_with_cache_control):
        if message.role != "user":
            continue
        content = message.content
        if not isinstance(content, list) or len(content) == 0:
            continue
        last_content_block = content[-1]
        if last_content_block["type"] == "tool_result":
            last_content_block["cache_control"] = {"type": "ephemeral"}
            break
    return messages_with_cache_control


def component_name_hook(name: str, server_info) -> str:
    """Hook to sanitize MCP component names for Anthropic."""
    raw_name = f"mcp_{server_info.name}.{name}"
    sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", raw_name)
    return sanitized_name

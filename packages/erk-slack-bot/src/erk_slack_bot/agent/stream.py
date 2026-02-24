from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
)

from erk_slack_bot.agent.events import (
    AgentEvent,
    AgentResult,
    TextDelta,
    ToolEnd,
    ToolStart,
    TurnEnd,
    TurnStart,
)


@dataclass(frozen=True)
class _ActiveToolBlock:
    tool_name: str
    tool_use_id: str


async def stream_agent_events(*, messages: AsyncIterator[Message]) -> AsyncIterator[AgentEvent]:
    turn_index = 0
    active_tool: _ActiveToolBlock | None = None
    turn_started = False

    async for message in messages:
        if isinstance(message, StreamEvent):
            event: dict[str, Any] = message.event
            event_type = event.get("type")

            if event_type == "message_start" and not turn_started:
                yield TurnStart(turn_index=turn_index)
                turn_started = True

            elif event_type == "content_block_start":
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    tool_name = content_block.get("name", "")
                    tool_use_id = content_block.get("id", "")
                    active_tool = _ActiveToolBlock(tool_name=tool_name, tool_use_id=tool_use_id)
                    yield ToolStart(tool_name=tool_name, tool_use_id=tool_use_id)

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        yield TextDelta(text=text)

            elif event_type == "content_block_stop":
                if active_tool is not None:
                    yield ToolEnd(
                        tool_name=active_tool.tool_name,
                        tool_use_id=active_tool.tool_use_id,
                    )
                    active_tool = None

        elif isinstance(message, AssistantMessage):
            yield TurnEnd(turn_index=turn_index)
            turn_index += 1
            turn_started = False

        elif isinstance(message, ResultMessage):
            usage = message.usage or {}
            yield AgentResult(
                session_id=message.session_id,
                num_turns=message.num_turns,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )

        elif isinstance(message, SystemMessage):
            continue

import logging
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

from erkbot.agent.events import (
    AgentEvent,
    AgentResult,
    TextDelta,
    ToolEnd,
    ToolStart,
    TurnEnd,
    TurnStart,
)

logger = logging.getLogger(__name__)


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
                logger.info("Turn %d started", turn_index)
                yield TurnStart(turn_index=turn_index)
                turn_started = True

            elif event_type == "content_block_start":
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    tool_name = content_block.get("name", "")
                    tool_use_id = content_block.get("id", "")
                    active_tool = _ActiveToolBlock(tool_name=tool_name, tool_use_id=tool_use_id)
                    logger.info("Tool started: %s (id=%s)", tool_name, tool_use_id)
                    yield ToolStart(tool_name=tool_name, tool_use_id=tool_use_id)

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        logger.debug("TextDelta: %s", text[:80])
                        yield TextDelta(text=text)

            elif event_type == "content_block_stop":
                if active_tool is not None:
                    logger.info(
                        "Tool ended: %s (id=%s)", active_tool.tool_name, active_tool.tool_use_id
                    )
                    yield ToolEnd(
                        tool_name=active_tool.tool_name,
                        tool_use_id=active_tool.tool_use_id,
                    )
                    active_tool = None

        elif isinstance(message, AssistantMessage):
            logger.info("Turn %d ended", turn_index)
            yield TurnEnd(turn_index=turn_index)
            turn_index += 1
            turn_started = False

        elif isinstance(message, ResultMessage):
            usage = message.usage or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            logger.info(
                "Agent result: session=%s turns=%d input_tokens=%d output_tokens=%d",
                message.session_id,
                message.num_turns,
                input_tokens,
                output_tokens,
            )
            yield AgentResult(
                session_id=message.session_id,
                num_turns=message.num_turns,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        elif isinstance(message, SystemMessage):
            continue

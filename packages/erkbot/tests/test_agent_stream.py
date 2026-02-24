import unittest
from collections.abc import AsyncIterator

from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
)
from erkbot.agent.events import (
    AgentResult,
    TextDelta,
    ToolEnd,
    ToolStart,
    TurnEnd,
    TurnStart,
)
from erkbot.agent.stream import stream_agent_events


async def _async_messages(items: list[Message]) -> AsyncIterator[Message]:
    for item in items:
        yield item


def _stream_event(event: dict) -> StreamEvent:
    return StreamEvent(uuid="u", session_id="s", event=event)


class TestStreamAgentEvents(unittest.IsolatedAsyncioTestCase):
    async def _collect(self, messages: list[Message]) -> list:
        events = []
        async for event in stream_agent_events(messages=_async_messages(messages)):
            events.append(event)
        return events

    async def test_text_delta_from_content_block_delta(self) -> None:
        messages: list[Message] = [
            _stream_event({"type": "message_start"}),
            _stream_event(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Hello"},
                }
            ),
        ]
        events = await self._collect(messages)
        self.assertEqual(events, [TurnStart(turn_index=0), TextDelta(text="Hello")])

    async def test_tool_start_and_end(self) -> None:
        messages: list[Message] = [
            _stream_event({"type": "message_start"}),
            _stream_event(
                {
                    "type": "content_block_start",
                    "content_block": {"type": "tool_use", "id": "tu_1", "name": "bash"},
                }
            ),
            _stream_event({"type": "content_block_stop"}),
        ]
        events = await self._collect(messages)
        self.assertEqual(
            events,
            [
                TurnStart(turn_index=0),
                ToolStart(tool_name="bash", tool_use_id="tu_1"),
                ToolEnd(tool_name="bash", tool_use_id="tu_1"),
            ],
        )

    async def test_turn_lifecycle(self) -> None:
        messages: list[Message] = [
            _stream_event({"type": "message_start"}),
            _stream_event(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "hi"},
                }
            ),
            AssistantMessage(content=[TextBlock(text="hi")], model="test"),
            _stream_event({"type": "message_start"}),
        ]
        events = await self._collect(messages)
        self.assertEqual(
            events,
            [
                TurnStart(turn_index=0),
                TextDelta(text="hi"),
                TurnEnd(turn_index=0),
                TurnStart(turn_index=1),
            ],
        )

    async def test_result_message_extracts_tokens(self) -> None:
        messages: list[Message] = [
            ResultMessage(
                subtype="end",
                duration_ms=100,
                duration_api_ms=80,
                is_error=False,
                num_turns=3,
                session_id="sess_1",
                usage={"input_tokens": 500, "output_tokens": 200},
            ),
        ]
        events = await self._collect(messages)
        self.assertEqual(
            events,
            [
                AgentResult(
                    session_id="sess_1",
                    num_turns=3,
                    input_tokens=500,
                    output_tokens=200,
                ),
            ],
        )

    async def test_result_message_no_usage(self) -> None:
        messages: list[Message] = [
            ResultMessage(
                subtype="end",
                duration_ms=100,
                duration_api_ms=80,
                is_error=False,
                num_turns=1,
                session_id="sess_2",
                usage=None,
            ),
        ]
        events = await self._collect(messages)
        self.assertEqual(
            events,
            [
                AgentResult(
                    session_id="sess_2",
                    num_turns=1,
                    input_tokens=0,
                    output_tokens=0,
                ),
            ],
        )

    async def test_system_message_skipped(self) -> None:
        messages: list[Message] = [
            SystemMessage(subtype="init", data={"info": "started"}),
        ]
        events = await self._collect(messages)
        self.assertEqual(events, [])

    async def test_no_duplicate_turn_start(self) -> None:
        messages: list[Message] = [
            _stream_event({"type": "message_start"}),
            _stream_event({"type": "message_start"}),
            _stream_event(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "only one turn"},
                }
            ),
        ]
        events = await self._collect(messages)
        self.assertEqual(
            events,
            [TurnStart(turn_index=0), TextDelta(text="only one turn")],
        )

    async def test_content_block_stop_without_tool(self) -> None:
        messages: list[Message] = [
            _stream_event({"type": "message_start"}),
            _stream_event(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "hi"},
                }
            ),
            _stream_event({"type": "content_block_stop"}),
        ]
        events = await self._collect(messages)
        self.assertEqual(
            events,
            [TurnStart(turn_index=0), TextDelta(text="hi")],
        )

    async def test_empty_text_delta_skipped(self) -> None:
        messages: list[Message] = [
            _stream_event({"type": "message_start"}),
            _stream_event(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": ""},
                }
            ),
        ]
        events = await self._collect(messages)
        self.assertEqual(events, [TurnStart(turn_index=0)])


if __name__ == "__main__":
    unittest.main()

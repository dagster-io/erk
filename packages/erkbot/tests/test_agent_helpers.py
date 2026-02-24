import unittest
from collections.abc import AsyncIterator

from erkbot.agent.events import (
    AgentEvent,
    AgentResult,
    TextDelta,
    ToolStart,
    TurnEnd,
    TurnStart,
)
from erkbot.agent.helpers import accumulate_text, collect_events, extract_result


async def _async_iter(items: list[AgentEvent]) -> AsyncIterator[AgentEvent]:
    for item in items:
        yield item


class TestAccumulateText(unittest.IsolatedAsyncioTestCase):
    async def test_joins_text_deltas(self) -> None:
        events = [
            TextDelta(text="Hello"),
            TextDelta(text=" "),
            TextDelta(text="world"),
        ]
        result = await accumulate_text(events=_async_iter(events))
        self.assertEqual(result, "Hello world")

    async def test_ignores_non_text_events(self) -> None:
        events: list[AgentEvent] = [
            TurnStart(turn_index=0),
            TextDelta(text="hi"),
            ToolStart(tool_name="bash", tool_use_id="tu_1"),
            TextDelta(text="!"),
            TurnEnd(turn_index=0),
        ]
        result = await accumulate_text(events=_async_iter(events))
        self.assertEqual(result, "hi!")

    async def test_empty_stream(self) -> None:
        result = await accumulate_text(events=_async_iter([]))
        self.assertEqual(result, "")

    async def test_no_text_events(self) -> None:
        events: list[AgentEvent] = [
            TurnStart(turn_index=0),
            TurnEnd(turn_index=0),
        ]
        result = await accumulate_text(events=_async_iter(events))
        self.assertEqual(result, "")


class TestCollectEvents(unittest.IsolatedAsyncioTestCase):
    async def test_collects_all_events(self) -> None:
        events: list[AgentEvent] = [
            TurnStart(turn_index=0),
            TextDelta(text="hi"),
            TurnEnd(turn_index=0),
        ]
        result = await collect_events(events=_async_iter(events))
        self.assertEqual(result, events)

    async def test_empty_stream(self) -> None:
        result = await collect_events(events=_async_iter([]))
        self.assertEqual(result, [])


class TestExtractResult(unittest.IsolatedAsyncioTestCase):
    def test_finds_result_at_end(self) -> None:
        agent_result = AgentResult(session_id="s", num_turns=2, input_tokens=50, output_tokens=25)
        events: list[AgentEvent] = [
            TurnStart(turn_index=0),
            TextDelta(text="hi"),
            TurnEnd(turn_index=0),
            agent_result,
        ]
        self.assertEqual(extract_result(events=events), agent_result)

    def test_finds_result_not_at_end(self) -> None:
        agent_result = AgentResult(session_id="s", num_turns=1, input_tokens=10, output_tokens=5)
        events: list[AgentEvent] = [
            agent_result,
            TurnStart(turn_index=0),
            TextDelta(text="extra"),
        ]
        self.assertEqual(extract_result(events=events), agent_result)

    def test_returns_none_when_absent(self) -> None:
        events: list[AgentEvent] = [
            TurnStart(turn_index=0),
            TextDelta(text="hi"),
            TurnEnd(turn_index=0),
        ]
        self.assertIsNone(extract_result(events=events))

    def test_returns_none_for_empty_list(self) -> None:
        self.assertIsNone(extract_result(events=[]))

    def test_returns_last_result_when_multiple(self) -> None:
        first = AgentResult(session_id="s1", num_turns=1, input_tokens=10, output_tokens=5)
        second = AgentResult(session_id="s2", num_turns=2, input_tokens=20, output_tokens=10)
        events: list[AgentEvent] = [first, TextDelta(text="hi"), second]
        self.assertEqual(extract_result(events=events), second)


if __name__ == "__main__":
    unittest.main()

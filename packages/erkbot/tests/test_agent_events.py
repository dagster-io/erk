import unittest
from dataclasses import FrozenInstanceError

from erk_slack_bot.agent.events import (
    AgentEvent,
    AgentResult,
    TextDelta,
    ToolEnd,
    ToolStart,
    TurnEnd,
    TurnStart,
)


class TestEventConstruction(unittest.TestCase):
    def test_text_delta(self) -> None:
        event = TextDelta(text="hello")
        self.assertEqual(event.text, "hello")

    def test_tool_start(self) -> None:
        event = ToolStart(tool_name="bash", tool_use_id="tu_1")
        self.assertEqual(event.tool_name, "bash")
        self.assertEqual(event.tool_use_id, "tu_1")

    def test_tool_end(self) -> None:
        event = ToolEnd(tool_name="bash", tool_use_id="tu_1")
        self.assertEqual(event.tool_name, "bash")
        self.assertEqual(event.tool_use_id, "tu_1")

    def test_turn_start(self) -> None:
        event = TurnStart(turn_index=0)
        self.assertEqual(event.turn_index, 0)

    def test_turn_end(self) -> None:
        event = TurnEnd(turn_index=2)
        self.assertEqual(event.turn_index, 2)

    def test_agent_result(self) -> None:
        event = AgentResult(
            session_id="sess_1",
            num_turns=3,
            input_tokens=100,
            output_tokens=50,
        )
        self.assertEqual(event.session_id, "sess_1")
        self.assertEqual(event.num_turns, 3)
        self.assertEqual(event.input_tokens, 100)
        self.assertEqual(event.output_tokens, 50)

    def test_agent_result_none_session(self) -> None:
        event = AgentResult(
            session_id=None,
            num_turns=1,
            input_tokens=0,
            output_tokens=0,
        )
        self.assertIsNone(event.session_id)


class TestEventEquality(unittest.TestCase):
    def test_text_delta_equality(self) -> None:
        a = TextDelta(text="hi")
        b = TextDelta(text="hi")
        self.assertEqual(a, b)

    def test_text_delta_inequality(self) -> None:
        a = TextDelta(text="hi")
        b = TextDelta(text="bye")
        self.assertNotEqual(a, b)

    def test_tool_start_equality(self) -> None:
        a = ToolStart(tool_name="bash", tool_use_id="tu_1")
        b = ToolStart(tool_name="bash", tool_use_id="tu_1")
        self.assertEqual(a, b)

    def test_frozen_text_delta(self) -> None:
        event = TextDelta(text="hi")
        with self.assertRaises(FrozenInstanceError):
            event.text = "bye"  # type: ignore[misc]

    def test_frozen_agent_result(self) -> None:
        event = AgentResult(session_id="s", num_turns=1, input_tokens=0, output_tokens=0)
        with self.assertRaises(FrozenInstanceError):
            event.num_turns = 5  # type: ignore[misc]


class TestAgentEventUnion(unittest.TestCase):
    def test_all_types_in_union(self) -> None:
        events: list[AgentEvent] = [
            TextDelta(text="x"),
            ToolStart(tool_name="bash", tool_use_id="tu_1"),
            ToolEnd(tool_name="bash", tool_use_id="tu_1"),
            TurnStart(turn_index=0),
            TurnEnd(turn_index=0),
            AgentResult(session_id="s", num_turns=1, input_tokens=10, output_tokens=5),
        ]
        expected_types = [TextDelta, ToolStart, ToolEnd, TurnStart, TurnEnd, AgentResult]
        for event, expected_type in zip(events, expected_types, strict=True):
            self.assertIsInstance(event, expected_type)


if __name__ == "__main__":
    unittest.main()

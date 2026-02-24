# NOTE: @patch usage is deliberate here. These tests verify the wiring between
# ErkBot and the claude-agent-sdk third-party library (query/stream_agent_events),
# which cannot be replaced with erk gateway fakes.
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from erkbot.agent.bot import ErkBot
from erkbot.agent.events import AgentResult, TextDelta, TurnEnd, TurnStart


async def _fake_stream_agent_events(*, messages):
    yield TurnStart(turn_index=0)
    yield TextDelta(text="Hello ")
    yield TextDelta(text="world")
    yield TurnEnd(turn_index=0)
    yield AgentResult(session_id="sess-1", num_turns=1, input_tokens=10, output_tokens=5)


class TestErkBot(unittest.IsolatedAsyncioTestCase):
    def _make_bot(self) -> ErkBot:
        return ErkBot(
            model="claude-sonnet-4-20250514",
            max_turns=5,
            cwd=Path("/tmp/test"),
            system_prompt="You are a test bot.",
            permission_mode="bypassPermissions",
        )

    @patch("erkbot.agent.bot.query")
    @patch("erkbot.agent.bot.stream_agent_events", side_effect=_fake_stream_agent_events)
    async def test_chat_stream_yields_events(
        self, mock_stream: AsyncMock, mock_query: AsyncMock
    ) -> None:
        bot = self._make_bot()
        events = []
        async for event in bot.chat_stream(prompt="hello"):
            events.append(event)

        self.assertEqual(len(events), 5)
        self.assertIsInstance(events[0], TurnStart)
        self.assertIsInstance(events[1], TextDelta)
        self.assertEqual(events[1].text, "Hello ")
        self.assertIsInstance(events[2], TextDelta)
        self.assertEqual(events[2].text, "world")
        self.assertIsInstance(events[3], TurnEnd)
        self.assertIsInstance(events[4], AgentResult)

    @patch("erkbot.agent.bot.query")
    @patch("erkbot.agent.bot.stream_agent_events", side_effect=_fake_stream_agent_events)
    async def test_chat_stream_passes_correct_options(
        self, mock_stream: AsyncMock, mock_query: AsyncMock
    ) -> None:
        bot = self._make_bot()
        async for _ in bot.chat_stream(prompt="hello"):
            pass

        mock_query.assert_called_once()
        call_kwargs = mock_query.call_args[1]
        self.assertEqual(call_kwargs["prompt"], "hello")
        options = call_kwargs["options"]
        self.assertEqual(options.model, "claude-sonnet-4-20250514")
        self.assertEqual(options.max_turns, 5)
        self.assertEqual(options.cwd, "/tmp/test")
        self.assertEqual(options.system_prompt, "You are a test bot.")
        self.assertEqual(options.permission_mode, "bypassPermissions")


if __name__ == "__main__":
    unittest.main()

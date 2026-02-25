import unittest
from unittest.mock import AsyncMock, MagicMock

from erkbot.agent.events import AgentResult, TextDelta, ToolEnd, ToolStart, TurnEnd, TurnStart
from erkbot.agent_handler import _build_progress_display, run_agent_background

from erk_shared.gateway.time.fake import FakeTime


class TestBuildProgressDisplay(unittest.TestCase):
    def test_tool_active_no_text(self) -> None:
        result = _build_progress_display(text="", tool_active=True)
        self.assertIn("Thinking...", result)

    def test_responding_with_text(self) -> None:
        result = _build_progress_display(text="some output", tool_active=False)
        self.assertIn("Responding...", result)
        self.assertIn("some output", result)

    def test_truncates_long_text(self) -> None:
        long_text = "x" * 3000
        result = _build_progress_display(text=long_text, tool_active=False)
        # Should contain truncated text (last 2000 chars)
        self.assertIn("x" * 2000, result)
        self.assertNotIn("x" * 3000, result)


class TestRunAgentBackground(unittest.IsolatedAsyncioTestCase):
    def _make_bot(self, events):
        bot = MagicMock()

        async def fake_chat_stream(*, prompt):
            for event in events:
                yield event

        bot.chat_stream = fake_chat_stream
        return bot

    async def test_full_lifecycle_success(self) -> None:
        fake_time = FakeTime(monotonic_values=[100.0])

        events = [
            TurnStart(turn_index=0),
            TextDelta(text="Hello "),
            TextDelta(text="world!"),
            TurnEnd(turn_index=0),
            AgentResult(session_id="s1", num_turns=1, input_tokens=10, output_tokens=5),
        ]
        bot = self._make_bot(events)
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=False,
            suggested_reply_blocks=[],
        )

        # Should have posted initial status
        client.chat_postMessage.assert_any_call(
            channel="C1", text="🤖 Thinking...", thread_ts="1.23"
        )
        # Should have removed eyes emoji
        client.reactions_remove.assert_any_call(channel="C1", timestamp="0.99", name="eyes")
        # Should have added success result emoji
        client.reactions_add.assert_any_call(
            channel="C1", timestamp="0.99", name="white_check_mark"
        )

    async def test_error_in_stream(self) -> None:
        fake_time = FakeTime(monotonic_values=[0.0])

        bot = MagicMock()

        async def failing_stream(*, prompt):
            yield TurnStart(turn_index=0)
            raise RuntimeError("stream failed")

        bot.chat_stream = failing_stream
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=False,
            suggested_reply_blocks=[],
        )

        # Should post error message
        client.chat_postMessage.assert_any_call(
            channel="C1",
            text="🤖 Agent encountered an error.",
            thread_ts="1.23",
        )
        # Should still add failure emoji
        client.reactions_add.assert_any_call(channel="C1", timestamp="0.99", name="x")

    async def test_empty_response(self) -> None:
        fake_time = FakeTime(monotonic_values=[100.0])

        events = [
            TurnStart(turn_index=0),
            TurnEnd(turn_index=0),
            AgentResult(session_id="s1", num_turns=1, input_tokens=10, output_tokens=0),
        ]
        bot = self._make_bot(events)
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=False,
            suggested_reply_blocks=[],
        )

        # Should post "no response" message
        client.chat_postMessage.assert_any_call(
            channel="C1",
            text="(No response generated.)",
            thread_ts="1.23",
        )

    async def test_tool_events_track_active_state(self) -> None:
        fake_time = FakeTime(monotonic_values=[2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0])

        events = [
            TurnStart(turn_index=0),
            ToolStart(tool_name="Bash", tool_use_id="tu1"),
            ToolEnd(tool_name="Bash", tool_use_id="tu1"),
            TextDelta(text="Done."),
            TurnEnd(turn_index=0),
            AgentResult(session_id="s1", num_turns=1, input_tokens=10, output_tokens=5),
        ]
        bot = self._make_bot(events)
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=False,
            suggested_reply_blocks=[],
        )

        # Should succeed (checkmark emoji)
        client.reactions_add.assert_any_call(
            channel="C1", timestamp="0.99", name="white_check_mark"
        )

    async def test_suggested_replies_posted_after_response(self) -> None:
        fake_time = FakeTime(monotonic_values=[100.0])

        events = [
            TurnStart(turn_index=0),
            TextDelta(text="Hello!"),
            TurnEnd(turn_index=0),
            AgentResult(session_id="s1", num_turns=1, input_tokens=10, output_tokens=5),
        ]
        bot = self._make_bot(events)
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}
        fake_blocks = [{"type": "actions", "elements": []}]

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=True,
            suggested_reply_blocks=fake_blocks,
        )

        client.chat_postMessage.assert_any_call(
            channel="C1",
            blocks=fake_blocks,
            text="Suggested follow-ups",
            thread_ts="1.23",
        )

    async def test_suggested_replies_not_posted_when_disabled(self) -> None:
        fake_time = FakeTime(monotonic_values=[100.0])

        events = [
            TurnStart(turn_index=0),
            TextDelta(text="Hello!"),
            TurnEnd(turn_index=0),
            AgentResult(session_id="s1", num_turns=1, input_tokens=10, output_tokens=5),
        ]
        bot = self._make_bot(events)
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}
        fake_blocks = [{"type": "actions", "elements": []}]

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=False,
            suggested_reply_blocks=fake_blocks,
        )

        # Should NOT have posted suggested replies
        for call in client.chat_postMessage.call_args_list:
            self.assertNotEqual(call.kwargs.get("text"), "Suggested follow-ups")

    async def test_suggested_replies_not_posted_on_error(self) -> None:
        fake_time = FakeTime(monotonic_values=[0.0])

        bot = MagicMock()

        async def failing_stream(*, prompt):
            yield TurnStart(turn_index=0)
            raise RuntimeError("stream failed")

        bot.chat_stream = failing_stream
        client = AsyncMock()
        client.chat_postMessage.return_value = {"ts": "2.34"}
        fake_blocks = [{"type": "actions", "elements": []}]

        await run_agent_background(
            client=client,
            channel="C1",
            reply_thread_ts="1.23",
            source_ts="0.99",
            prompt="hello",
            bot=bot,
            time=fake_time,
            progress_update_interval_seconds=1.0,
            max_slack_code_block_chars=2800,
            enable_suggested_replies=True,
            suggested_reply_blocks=fake_blocks,
        )

        # Should NOT have posted suggested replies on error path
        for call in client.chat_postMessage.call_args_list:
            self.assertNotEqual(call.kwargs.get("text"), "Suggested follow-ups")


if __name__ == "__main__":
    unittest.main()

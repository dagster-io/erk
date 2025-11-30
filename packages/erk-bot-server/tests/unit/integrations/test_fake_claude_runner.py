"""Tests for FakeClaudeRunner implementation."""

import attrs
import pytest
from erk_bot_server.integrations.claude_runner.fake import ExecuteCall, FakeClaudeRunner
from erk_bot_server.models.session import StreamEvent


class TestFakeClaudeRunner:
    """Tests for the FakeClaudeRunner fake implementation."""

    @pytest.fixture
    def runner(self) -> FakeClaudeRunner:
        """Provide a fresh FakeClaudeRunner for each test."""
        return FakeClaudeRunner()

    async def test_execute_returns_default_response(self, runner: FakeClaudeRunner) -> None:
        """Executing without configured response returns default."""
        events: list[StreamEvent] = []
        async for event in runner.execute_message(
            session_id="session-1",
            message="Hello",
            working_directory="/repo",
            timeout_seconds=300,
        ):
            events.append(event)

        assert len(events) == 2
        assert events[0].event_type == "text"
        assert events[0].data["content"] == "Hello! I can help you with that."
        assert events[1].event_type == "done"
        assert events[1].data["success"] is True

    async def test_execute_records_call(self, runner: FakeClaudeRunner) -> None:
        """Executing records the call for assertions."""
        async for _ in runner.execute_message(
            session_id="session-1",
            message="Test message",
            working_directory="/test/repo",
            timeout_seconds=120,
        ):
            pass

        assert len(runner.execute_calls) == 1
        call = runner.execute_calls[0]
        assert call.session_id == "session-1"
        assert call.message == "Test message"
        assert call.working_directory == "/test/repo"
        assert call.timeout_seconds == 120

    async def test_execute_with_custom_responses(self) -> None:
        """Executing with configured responses returns them."""
        custom_events = [
            StreamEvent("text", {"content": "Custom response"}),
            StreamEvent("done", {"success": True}),
        ]
        runner = FakeClaudeRunner(responses={"custom-session": custom_events})

        events: list[StreamEvent] = []
        async for event in runner.execute_message(
            session_id="custom-session",
            message="Hi",
            working_directory="/repo",
            timeout_seconds=300,
        ):
            events.append(event)

        assert len(events) == 2
        assert events[0].data["content"] == "Custom response"

    async def test_execute_with_custom_default_response(self) -> None:
        """Executing with custom default response uses it."""
        custom_default = [
            StreamEvent("text", {"content": "Default custom"}),
            StreamEvent("done", {"success": False}),
        ]
        runner = FakeClaudeRunner(default_response=custom_default)

        events: list[StreamEvent] = []
        async for event in runner.execute_message(
            session_id="any-session",
            message="Hi",
            working_directory="/repo",
            timeout_seconds=300,
        ):
            events.append(event)

        assert len(events) == 2
        assert events[0].data["content"] == "Default custom"
        assert events[1].data["success"] is False

    async def test_execute_falls_back_to_default_for_unknown_session(self) -> None:
        """Unknown session ID uses default response."""
        custom_events = [StreamEvent("text", {"content": "For specific session"})]
        runner = FakeClaudeRunner(responses={"specific": custom_events})

        events: list[StreamEvent] = []
        async for event in runner.execute_message(
            session_id="unknown",
            message="Hi",
            working_directory="/repo",
            timeout_seconds=300,
        ):
            events.append(event)

        # Should get default response, not the custom one
        assert events[0].data["content"] == "Hello! I can help you with that."

    async def test_multiple_executions_tracked(self, runner: FakeClaudeRunner) -> None:
        """Multiple executions are all tracked."""
        async for _ in runner.execute_message("s1", "msg1", "/repo1", 100):
            pass
        async for _ in runner.execute_message("s2", "msg2", "/repo2", 200):
            pass

        assert len(runner.execute_calls) == 2
        assert runner.execute_calls[0].session_id == "s1"
        assert runner.execute_calls[1].session_id == "s2"

    async def test_execute_calls_returns_copy(self, runner: FakeClaudeRunner) -> None:
        """The execute_calls property returns a copy."""
        async for _ in runner.execute_message("s1", "msg", "/repo", 100):
            pass

        calls_copy = runner.execute_calls
        calls_copy.clear()

        assert len(runner.execute_calls) == 1


class TestExecuteCall:
    """Tests for the ExecuteCall dataclass."""

    def test_execute_call_is_frozen(self) -> None:
        """ExecuteCall is immutable."""
        call = ExecuteCall(
            session_id="s1",
            message="msg",
            working_directory="/repo",
            timeout_seconds=100,
        )

        with pytest.raises(attrs.FrozenInstanceError):
            call.session_id = "new-id"  # type: ignore[misc]

    def test_execute_call_fields(self) -> None:
        """ExecuteCall stores all fields correctly."""
        call = ExecuteCall(
            session_id="session-123",
            message="Test message",
            working_directory="/test/repo",
            timeout_seconds=150,
        )

        assert call.session_id == "session-123"
        assert call.message == "Test message"
        assert call.working_directory == "/test/repo"
        assert call.timeout_seconds == 150

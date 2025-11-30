"""Fake Claude runner for testing."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from erk_bot_server.integrations.claude_runner.abc import ClaudeRunner
from erk_bot_server.models.session import StreamEvent


@dataclass(frozen=True)
class ExecuteCall:
    """Record of an execute_message call for test assertions."""

    session_id: str
    message: str
    working_directory: str
    timeout_seconds: int


class FakeClaudeRunner(ClaudeRunner):
    """In-memory fake implementation for testing.

    Provides canned responses and tracks all calls for assertions.
    """

    def __init__(
        self,
        responses: dict[str, list[StreamEvent]] | None = None,
        default_response: list[StreamEvent] | None = None,
    ) -> None:
        """Create FakeClaudeRunner.

        Args:
            responses: Optional mapping of session_id -> events to yield
            default_response: Optional default events if session_id not in responses
        """
        self._responses = responses or {}
        self._default_response = default_response or [
            StreamEvent("text", {"content": "Hello! I can help you with that."}),
            StreamEvent("done", {"success": True}),
        ]
        self._execute_calls: list[ExecuteCall] = []

    @property
    def execute_calls(self) -> list[ExecuteCall]:
        """Get list of execute_message calls for test assertions."""
        return self._execute_calls.copy()

    async def execute_message(
        self,
        session_id: str,
        message: str,
        working_directory: str,
        timeout_seconds: int,
    ) -> AsyncIterator[StreamEvent]:
        """Yield canned responses for testing.

        Records the call for test assertions, then yields
        configured responses for the session_id, or default response.
        """
        self._execute_calls.append(
            ExecuteCall(
                session_id=session_id,
                message=message,
                working_directory=working_directory,
                timeout_seconds=timeout_seconds,
            )
        )

        events = self._responses.get(session_id, self._default_response)
        for event in events:
            yield event

"""Abstract base class for Claude CLI execution."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from erk_bot_server.models.session import StreamEvent


class ClaudeRunner(ABC):
    """Abstract interface for executing Claude CLI commands.

    Implementations include:
    - FakeClaudeRunner: Canned responses for testing
    - RealClaudeRunner: Subprocess execution for production
    """

    @abstractmethod
    def execute_message(
        self,
        session_id: str,
        message: str,
        working_directory: str,
        timeout_seconds: int,
    ) -> AsyncIterator[StreamEvent]:
        """Execute a message in Claude CLI and stream the response.

        Args:
            session_id: The Claude CLI session ID to resume
            message: The user message to send
            working_directory: Directory to run Claude in
            timeout_seconds: Maximum time to wait for response

        Yields:
            StreamEvent objects for each piece of output

        Note:
            This is an async generator that yields StreamEvents.
            The final event should have event_type="done".
        """
        ...

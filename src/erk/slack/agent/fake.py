"""Fake implementation of AgentSpawner for testing."""

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from erk.slack.agent.abc import AgentResult, AgentSpawner


@dataclass
class SpawnCall:
    """Record of a spawn() call for test assertions.

    Attributes:
        channel: The Slack channel ID
        thread_ts: The thread timestamp
        message: The user's message text
        repo_path: Path to the repository
        session_id: Session ID if provided
    """

    channel: str
    thread_ts: str
    message: str
    repo_path: Path
    session_id: str | None


@dataclass
class FakeAgentSpawner(AgentSpawner):
    """Fake implementation of AgentSpawner for testing.

    Allows tests to configure behavior and inspect calls.

    Example:
        >>> spawner = FakeAgentSpawner()
        >>> spawner.set_next_result(success=True)
        >>> result = spawner.spawn("C123", "1234.5678", "hello", Path("/repo"))
        >>> assert result.success
        >>> assert len(spawner.spawn_calls) == 1
    """

    _next_success: bool = True
    _next_error: str | None = None
    _next_session_id: str | None = None
    _spawn_calls: list[SpawnCall] = field(default_factory=list)

    def spawn(
        self,
        channel: str,
        thread_ts: str,
        message: str,
        repo_path: Path,
        session_id: str | None = None,
    ) -> AgentResult:
        """Record the spawn call and return configured result.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp
            message: The user's message text
            repo_path: Path to the repository
            session_id: Optional session ID to resume

        Returns:
            AgentResult with configured success/error status
        """
        call = SpawnCall(
            channel=channel,
            thread_ts=thread_ts,
            message=message,
            repo_path=repo_path,
            session_id=session_id,
        )
        self._spawn_calls.append(call)

        # Generate session ID if not configured
        result_session_id = self._next_session_id
        if result_session_id is None:
            result_session_id = str(uuid4())

        return AgentResult(
            session_id=result_session_id,
            success=self._next_success,
            error_message=self._next_error,
        )

    def set_next_result(
        self,
        success: bool = True,
        error_message: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Configure the result for the next spawn() call.

        Args:
            success: Whether the next spawn should succeed
            error_message: Error message if not successful
            session_id: Session ID to return (generates UUID if None)
        """
        self._next_success = success
        self._next_error = error_message
        self._next_session_id = session_id

    @property
    def spawn_calls(self) -> list[SpawnCall]:
        """Read-only access to recorded spawn calls.

        Returns:
            Copy of the spawn calls list
        """
        return list(self._spawn_calls)

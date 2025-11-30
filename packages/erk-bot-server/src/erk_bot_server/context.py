"""Application context with dependency injection."""

from dataclasses import dataclass

from erk_bot_server.integrations.claude_runner.abc import ClaudeRunner
from erk_bot_server.integrations.session_store.abc import SessionStore


@dataclass(frozen=True)
class ServerContext:
    """Immutable context holding all dependencies for server operations.

    Created at application startup and stored in FastAPI app state.
    Frozen to prevent accidental modification at runtime.
    """

    session_store: SessionStore
    claude_runner: ClaudeRunner

    @staticmethod
    def for_test(
        session_store: SessionStore | None = None,
        claude_runner: ClaudeRunner | None = None,
    ) -> "ServerContext":
        """Create test context with fake implementations.

        Args:
            session_store: Optional SessionStore (defaults to FakeSessionStore)
            claude_runner: Optional ClaudeRunner (defaults to FakeClaudeRunner)

        Returns:
            ServerContext configured for testing
        """
        from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
        from erk_bot_server.integrations.session_store.fake import FakeSessionStore

        return ServerContext(
            session_store=session_store or FakeSessionStore(),
            claude_runner=claude_runner or FakeClaudeRunner(),
        )

"""Business logic for session management."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from erk_bot_server.integrations.claude_runner.abc import ClaudeRunner
from erk_bot_server.integrations.session_store.abc import SessionStore
from erk_bot_server.models.session import Session, StreamEvent


@dataclass(frozen=True)
class SessionService:
    """Business logic for managing Claude CLI sessions.

    Coordinates between SessionStore and ClaudeRunner to provide
    session management and message handling.
    """

    session_store: SessionStore
    claude_runner: ClaudeRunner

    async def create_session(self, external_id: str | None, working_directory: str) -> Session:
        """Create a new session.

        Args:
            external_id: Optional external identifier (e.g., Slack thread ID)
            working_directory: Path to working directory for this session

        Returns:
            The newly created Session
        """
        return await self.session_store.create_session(external_id, working_directory)

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session's unique identifier

        Returns:
            The Session if found, None otherwise
        """
        return await self.session_store.get_session(session_id)

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of all sessions, ordered by creation time (newest first)
        """
        return await self.session_store.list_sessions()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if session was found and deleted, False otherwise
        """
        return await self.session_store.delete_session(session_id)

    async def send_message(
        self, session_id: str, content: str, timeout_seconds: int = 300
    ) -> AsyncIterator[StreamEvent]:
        """Send a message to a session and stream the response.

        Args:
            session_id: The session's unique identifier
            content: The message content to send
            timeout_seconds: Maximum time to wait for response

        Yields:
            StreamEvent objects for each piece of output

        Raises:
            ValueError: If session does not exist
        """
        session = await self.session_store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        # Update status to processing
        await self.session_store.update_session(session_id, status="processing")

        try:
            # Stream events from Claude
            async for event in self.claude_runner.execute_message(
                session_id=session_id,
                message=content,
                working_directory=session.working_directory,
                timeout_seconds=timeout_seconds,
            ):
                yield event

                # Check for completion or error
                if event.event_type == "done":
                    success = event.data.get("success", False)
                    new_status = "active" if success else "error"
                    await self.session_store.update_session(
                        session_id,
                        status=new_status,
                        message_count=session.message_count + 1,
                    )
                elif event.event_type == "error":
                    await self.session_store.update_session(session_id, status="error")

        except Exception:
            # Update status to error on exception
            await self.session_store.update_session(session_id, status="error")
            raise

    async def get_or_create_session_by_external_id(
        self, external_id: str, working_directory: str
    ) -> Session:
        """Get existing session by external ID, or create if not found.

        Useful for Slack integration where we want to reuse sessions
        for the same thread.

        Args:
            external_id: External identifier (e.g., Slack thread ID)
            working_directory: Path to working directory if creating new

        Returns:
            Existing or newly created Session
        """
        existing = await self.session_store.get_session_by_external_id(external_id)
        if existing is not None:
            return existing
        return await self.session_store.create_session(external_id, working_directory)

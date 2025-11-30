"""Abstract base class for session storage."""

from abc import ABC, abstractmethod

from erk_bot_server.models.session import Session


class SessionStore(ABC):
    """Abstract interface for session persistence.

    Implementations include:
    - FakeSessionStore: In-memory for testing
    - RealSessionStore: Redis-backed for production
    """

    @abstractmethod
    async def create_session(self, external_id: str | None, working_dir: str) -> Session:
        """Create a new session.

        Args:
            external_id: Optional external identifier (e.g., Slack thread ID)
            working_dir: Path to working directory for this session

        Returns:
            The newly created Session
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session's unique identifier

        Returns:
            The Session if found, None otherwise
        """
        ...

    @abstractmethod
    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of all sessions, ordered by creation time (newest first)
        """
        ...

    @abstractmethod
    async def update_session(
        self, session_id: str, status: str | None = None, message_count: int | None = None
    ) -> bool:
        """Update session fields.

        Args:
            session_id: The session's unique identifier
            status: Optional new status value
            message_count: Optional new message count

        Returns:
            True if session was found and updated, False otherwise
        """
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if session was found and deleted, False otherwise
        """
        ...

    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if session exists, False otherwise
        """
        ...

    @abstractmethod
    async def get_session_by_external_id(self, external_id: str) -> Session | None:
        """Get a session by external ID.

        Args:
            external_id: The external identifier (e.g., Slack thread ID)

        Returns:
            The Session if found, None otherwise
        """
        ...

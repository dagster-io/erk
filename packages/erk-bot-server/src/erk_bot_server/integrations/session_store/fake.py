"""Fake in-memory session store for testing."""

import uuid
from dataclasses import replace
from datetime import datetime

from erk_bot_server.integrations.session_store.abc import SessionStore
from erk_bot_server.models.session import Session


class FakeSessionStore(SessionStore):
    """In-memory fake implementation for testing.

    This class tracks all operations for test assertions.
    State is provided via constructor or captured during execution.
    """

    def __init__(
        self,
        sessions: dict[str, Session] | None = None,
        now: datetime | None = None,
    ) -> None:
        """Create FakeSessionStore.

        Args:
            sessions: Optional initial sessions (session_id -> Session)
            now: Optional fixed datetime for timestamps (defaults to datetime.now)
        """
        self._sessions: dict[str, Session] = sessions or {}
        self._external_id_map: dict[str, str] = {}  # external_id -> session_id
        self._now = now or datetime.now()

        # Build external_id map from initial sessions
        for session in self._sessions.values():
            if session.external_id is not None:
                self._external_id_map[session.external_id] = session.session_id

    @property
    def sessions(self) -> dict[str, Session]:
        """Get current sessions for test assertions."""
        return self._sessions.copy()

    async def create_session(self, external_id: str | None, working_dir: str) -> Session:
        """Create a new session in memory."""
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            external_id=external_id,
            working_directory=working_dir,
            status="active",
            created_at=self._now,
            last_activity=self._now,
            message_count=0,
        )
        self._sessions[session_id] = session
        if external_id is not None:
            self._external_id_map[external_id] = session_id
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get session by ID from memory."""
        if session_id not in self._sessions:
            return None
        return self._sessions[session_id]

    async def list_sessions(self) -> list[Session]:
        """List all sessions, newest first."""
        return sorted(
            self._sessions.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )

    async def update_session(
        self, session_id: str, status: str | None = None, message_count: int | None = None
    ) -> bool:
        """Update session fields in memory."""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        updates: dict[str, str | int | datetime] = {"last_activity": self._now}
        if status is not None:
            updates["status"] = status
        if message_count is not None:
            updates["message_count"] = message_count

        self._sessions[session_id] = replace(session, **updates)  # type: ignore[arg-type]
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory."""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        if session.external_id is not None:
            del self._external_id_map[session.external_id]
        del self._sessions[session_id]
        return True

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists in memory."""
        return session_id in self._sessions

    async def get_session_by_external_id(self, external_id: str) -> Session | None:
        """Get session by external ID from memory."""
        if external_id not in self._external_id_map:
            return None
        session_id = self._external_id_map[external_id]
        return await self.get_session(session_id)

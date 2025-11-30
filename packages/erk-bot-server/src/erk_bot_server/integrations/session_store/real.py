"""Redis-backed session store implementation."""

import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from erk_bot_server.integrations.session_store.abc import SessionStore
from erk_bot_server.models.session import Session


class RealSessionStore(SessionStore):
    """Production Redis-backed session store.

    Redis Schema:
    - erk:session:{session_id} - Hash containing session data
    - erk:external:{external_id} - String mapping external_id -> session_id
    """

    def __init__(self, redis_url: str) -> None:
        """Create RealSessionStore.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
        """
        self._redis_url = redis_url
        self._redis: Any = None  # Redis client, typed as Any due to incomplete stubs

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = redis.from_url(self._redis_url)  # type: ignore[no-untyped-call]

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis is not None:
            await self._redis.aclose()

    def _session_key(self, session_id: str) -> str:
        """Get Redis key for session hash."""
        return f"erk:session:{session_id}"

    def _external_key(self, external_id: str) -> str:
        """Get Redis key for external ID mapping."""
        return f"erk:external:{external_id}"

    def _session_from_hash(self, data: dict[bytes, bytes]) -> Session:
        """Convert Redis hash data to Session object."""
        return Session(
            session_id=data[b"session_id"].decode(),
            external_id=data[b"external_id"].decode() if data.get(b"external_id") else None,
            working_directory=data[b"working_directory"].decode(),
            status=data[b"status"].decode(),
            created_at=datetime.fromisoformat(data[b"created_at"].decode()),
            last_activity=datetime.fromisoformat(data[b"last_activity"].decode()),
            message_count=int(data[b"message_count"]),
        )

    def _session_to_hash(self, session: Session) -> dict[str, str]:
        """Convert Session object to Redis hash data."""
        return {
            "session_id": session.session_id,
            "external_id": session.external_id or "",
            "working_directory": session.working_directory,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "message_count": str(session.message_count),
        }

    async def create_session(self, external_id: str | None, working_dir: str) -> Session:
        """Create a new session in Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = Session(
            session_id=session_id,
            external_id=external_id,
            working_directory=working_dir,
            status="active",
            created_at=now,
            last_activity=now,
            message_count=0,
        )

        # Store session hash
        await self._redis.hset(
            self._session_key(session_id),
            mapping=self._session_to_hash(session),
        )

        # Store external ID mapping if provided
        if external_id is not None:
            await self._redis.set(self._external_key(external_id), session_id)

        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get session by ID from Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        data = await self._redis.hgetall(self._session_key(session_id))
        if not data:
            return None

        return self._session_from_hash(data)

    async def list_sessions(self) -> list[Session]:
        """List all sessions from Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        # Get all session keys
        keys = await self._redis.keys("erk:session:*")
        if not keys:
            return []

        # Get all sessions
        sessions: list[Session] = []
        for key in keys:
            data = await self._redis.hgetall(key)
            if data:
                sessions.append(self._session_from_hash(data))

        # Sort by created_at descending
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    async def update_session(
        self, session_id: str, status: str | None = None, message_count: int | None = None
    ) -> bool:
        """Update session fields in Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        key = self._session_key(session_id)

        # Check if session exists
        exists = await self._redis.exists(key)
        if not exists:
            return False

        # Build update mapping
        updates: dict[str, str] = {"last_activity": datetime.now().isoformat()}
        if status is not None:
            updates["status"] = status
        if message_count is not None:
            updates["message_count"] = str(message_count)

        await self._redis.hset(key, mapping=updates)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        key = self._session_key(session_id)

        # Get session to find external_id
        data = await self._redis.hgetall(key)
        if not data:
            return False

        # Delete external ID mapping if exists
        external_id = data.get(b"external_id", b"").decode()
        if external_id:
            await self._redis.delete(self._external_key(external_id))

        # Delete session
        await self._redis.delete(key)
        return True

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists in Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        return bool(await self._redis.exists(self._session_key(session_id)))

    async def get_session_by_external_id(self, external_id: str) -> Session | None:
        """Get session by external ID from Redis."""
        if self._redis is None:
            raise RuntimeError("Not connected to Redis")

        session_id = await self._redis.get(self._external_key(external_id))
        if session_id is None:
            return None

        return await self.get_session(session_id.decode())

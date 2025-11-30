"""Tests for FakeSessionStore implementation."""

from datetime import datetime

import pytest
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.models.session import Session


class TestFakeSessionStore:
    """Tests for the FakeSessionStore fake implementation."""

    @pytest.fixture
    def fixed_time(self) -> datetime:
        """Provide a fixed datetime for deterministic tests."""
        return datetime(2024, 1, 15, 10, 30, 0)

    @pytest.fixture
    def store(self, fixed_time: datetime) -> FakeSessionStore:
        """Provide a fresh FakeSessionStore for each test."""
        return FakeSessionStore(now=fixed_time)

    async def test_create_session_generates_uuid(self, store: FakeSessionStore) -> None:
        """Creating a session generates a unique UUID."""
        session = await store.create_session(None, "/path/to/repo")

        assert session.session_id is not None
        assert len(session.session_id) == 36  # UUID format

    async def test_create_session_stores_fields(
        self, store: FakeSessionStore, fixed_time: datetime
    ) -> None:
        """Creating a session stores all fields correctly."""
        session = await store.create_session("slack-123", "/path/to/repo")

        assert session.external_id == "slack-123"
        assert session.working_directory == "/path/to/repo"
        assert session.status == "active"
        assert session.created_at == fixed_time
        assert session.last_activity == fixed_time
        assert session.message_count == 0

    async def test_get_session_returns_none_for_unknown(self, store: FakeSessionStore) -> None:
        """Getting an unknown session returns None."""
        result = await store.get_session("unknown-id")

        assert result is None

    async def test_get_session_returns_created_session(self, store: FakeSessionStore) -> None:
        """Getting a session by ID returns the session."""
        created = await store.create_session(None, "/repo")

        result = await store.get_session(created.session_id)

        assert result == created

    async def test_list_sessions_empty_initially(self, store: FakeSessionStore) -> None:
        """Listing sessions returns empty list initially."""
        result = await store.list_sessions()

        assert result == []

    async def test_list_sessions_returns_all_sessions(self, store: FakeSessionStore) -> None:
        """Listing sessions returns all created sessions."""
        session1 = await store.create_session(None, "/repo1")
        session2 = await store.create_session(None, "/repo2")

        result = await store.list_sessions()

        assert len(result) == 2
        assert session1 in result
        assert session2 in result

    async def test_update_session_returns_false_for_unknown(self, store: FakeSessionStore) -> None:
        """Updating unknown session returns False."""
        result = await store.update_session("unknown-id", status="processing")

        assert result is False

    async def test_update_session_updates_status(self, store: FakeSessionStore) -> None:
        """Updating session status works correctly."""
        session = await store.create_session(None, "/repo")

        result = await store.update_session(session.session_id, status="processing")

        assert result is True
        updated = await store.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "processing"

    async def test_update_session_updates_message_count(self, store: FakeSessionStore) -> None:
        """Updating session message count works correctly."""
        session = await store.create_session(None, "/repo")

        result = await store.update_session(session.session_id, message_count=5)

        assert result is True
        updated = await store.get_session(session.session_id)
        assert updated is not None
        assert updated.message_count == 5

    async def test_delete_session_returns_false_for_unknown(self, store: FakeSessionStore) -> None:
        """Deleting unknown session returns False."""
        result = await store.delete_session("unknown-id")

        assert result is False

    async def test_delete_session_removes_session(self, store: FakeSessionStore) -> None:
        """Deleting a session removes it from the store."""
        session = await store.create_session(None, "/repo")

        result = await store.delete_session(session.session_id)

        assert result is True
        assert await store.get_session(session.session_id) is None

    async def test_session_exists_returns_false_for_unknown(self, store: FakeSessionStore) -> None:
        """Checking existence of unknown session returns False."""
        result = await store.session_exists("unknown-id")

        assert result is False

    async def test_session_exists_returns_true_for_existing(self, store: FakeSessionStore) -> None:
        """Checking existence of existing session returns True."""
        session = await store.create_session(None, "/repo")

        result = await store.session_exists(session.session_id)

        assert result is True

    async def test_get_session_by_external_id_returns_none_for_unknown(
        self, store: FakeSessionStore
    ) -> None:
        """Getting session by unknown external ID returns None."""
        result = await store.get_session_by_external_id("unknown-external")

        assert result is None

    async def test_get_session_by_external_id_finds_session(self, store: FakeSessionStore) -> None:
        """Getting session by external ID finds the session."""
        session = await store.create_session("slack-456", "/repo")

        result = await store.get_session_by_external_id("slack-456")

        assert result == session

    async def test_delete_session_clears_external_id_mapping(self, store: FakeSessionStore) -> None:
        """Deleting a session removes its external ID mapping."""
        session = await store.create_session("slack-789", "/repo")
        await store.delete_session(session.session_id)

        result = await store.get_session_by_external_id("slack-789")

        assert result is None

    async def test_sessions_property_returns_copy(self, store: FakeSessionStore) -> None:
        """The sessions property returns a copy, not the internal dict."""
        await store.create_session(None, "/repo")

        sessions_copy = store.sessions
        sessions_copy.clear()

        assert len(store.sessions) == 1

    async def test_initial_sessions_via_constructor(self, fixed_time: datetime) -> None:
        """Sessions can be provided via constructor."""
        initial_session = Session(
            session_id="preset-id",
            external_id="preset-external",
            working_directory="/preset/path",
            status="active",
            created_at=fixed_time,
            last_activity=fixed_time,
            message_count=10,
        )
        store = FakeSessionStore(
            sessions={"preset-id": initial_session},
            now=fixed_time,
        )

        result = await store.get_session("preset-id")

        assert result == initial_session

    async def test_initial_sessions_external_id_mapping(self, fixed_time: datetime) -> None:
        """Initial sessions have their external IDs indexed."""
        initial_session = Session(
            session_id="preset-id",
            external_id="preset-external",
            working_directory="/preset/path",
            status="active",
            created_at=fixed_time,
            last_activity=fixed_time,
            message_count=0,
        )
        store = FakeSessionStore(
            sessions={"preset-id": initial_session},
            now=fixed_time,
        )

        result = await store.get_session_by_external_id("preset-external")

        assert result == initial_session

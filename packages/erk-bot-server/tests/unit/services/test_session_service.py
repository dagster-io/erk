"""Tests for SessionService business logic."""

import pytest
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.models.session import Session, StreamEvent
from erk_bot_server.services.session_service import SessionService


class TestSessionServiceCreate:
    """Tests for SessionService.create_session."""

    @pytest.fixture
    def service(self) -> SessionService:
        """Provide SessionService with fakes."""
        return SessionService(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(),
        )

    async def test_create_session_returns_session(self, service: SessionService) -> None:
        """Creating a session returns a Session object."""
        result = await service.create_session(None, "/repo")

        assert isinstance(result, Session)
        assert result.working_directory == "/repo"
        assert result.status == "active"

    async def test_create_session_with_external_id(self, service: SessionService) -> None:
        """Creating a session with external ID stores it."""
        result = await service.create_session("slack-123", "/repo")

        assert result.external_id == "slack-123"


class TestSessionServiceGet:
    """Tests for SessionService.get_session."""

    @pytest.fixture
    def service(self) -> SessionService:
        """Provide SessionService with fakes."""
        return SessionService(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(),
        )

    async def test_get_session_returns_none_for_unknown(self, service: SessionService) -> None:
        """Getting unknown session returns None."""
        result = await service.get_session("unknown-id")

        assert result is None

    async def test_get_session_returns_created_session(self, service: SessionService) -> None:
        """Getting session returns the created session."""
        created = await service.create_session(None, "/repo")

        result = await service.get_session(created.session_id)

        assert result == created


class TestSessionServiceList:
    """Tests for SessionService.list_sessions."""

    @pytest.fixture
    def service(self) -> SessionService:
        """Provide SessionService with fakes."""
        return SessionService(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(),
        )

    async def test_list_sessions_empty_initially(self, service: SessionService) -> None:
        """Listing sessions returns empty list initially."""
        result = await service.list_sessions()

        assert result == []

    async def test_list_sessions_returns_all(self, service: SessionService) -> None:
        """Listing sessions returns all sessions."""
        session1 = await service.create_session(None, "/repo1")
        session2 = await service.create_session(None, "/repo2")

        result = await service.list_sessions()

        assert len(result) == 2
        assert session1 in result
        assert session2 in result


class TestSessionServiceDelete:
    """Tests for SessionService.delete_session."""

    @pytest.fixture
    def service(self) -> SessionService:
        """Provide SessionService with fakes."""
        return SessionService(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(),
        )

    async def test_delete_unknown_returns_false(self, service: SessionService) -> None:
        """Deleting unknown session returns False."""
        result = await service.delete_session("unknown-id")

        assert result is False

    async def test_delete_session_removes_it(self, service: SessionService) -> None:
        """Deleting a session removes it."""
        session = await service.create_session(None, "/repo")

        result = await service.delete_session(session.session_id)

        assert result is True
        assert await service.get_session(session.session_id) is None


class TestSessionServiceSendMessage:
    """Tests for SessionService.send_message."""

    async def test_send_message_raises_for_unknown_session(self) -> None:
        """Sending message to unknown session raises ValueError."""
        service = SessionService(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(),
        )

        with pytest.raises(ValueError, match="Session not found"):
            async for _ in service.send_message("unknown-id", "Hello"):
                pass

    async def test_send_message_streams_events(self) -> None:
        """Sending message streams events from Claude."""
        store = FakeSessionStore()
        runner = FakeClaudeRunner()
        service = SessionService(session_store=store, claude_runner=runner)

        session = await service.create_session(None, "/repo")

        events: list[StreamEvent] = []
        async for event in service.send_message(session.session_id, "Hello"):
            events.append(event)

        assert len(events) == 2
        assert events[0].event_type == "text"
        assert events[1].event_type == "done"

    async def test_send_message_updates_status_to_processing(self) -> None:
        """Sending message updates session status to processing."""
        store = FakeSessionStore()
        runner = FakeClaudeRunner()
        service = SessionService(session_store=store, claude_runner=runner)

        session = await service.create_session(None, "/repo")

        # Start processing but don't consume all events yet
        gen = service.send_message(session.session_id, "Hello")
        await gen.__anext__()  # Get first event

        # Session should now be processing
        updated = await store.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "processing"

        # Consume remaining events
        async for _ in gen:
            pass

    async def test_send_message_updates_status_on_success(self) -> None:
        """Successful message updates status to active."""
        store = FakeSessionStore()
        runner = FakeClaudeRunner(
            default_response=[
                StreamEvent("text", {"content": "Hi"}),
                StreamEvent("done", {"success": True}),
            ]
        )
        service = SessionService(session_store=store, claude_runner=runner)

        session = await service.create_session(None, "/repo")

        async for _ in service.send_message(session.session_id, "Hello"):
            pass

        updated = await store.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "active"
        assert updated.message_count == 1

    async def test_send_message_updates_status_on_failure(self) -> None:
        """Failed message updates status to error."""
        store = FakeSessionStore()
        runner = FakeClaudeRunner(
            default_response=[
                StreamEvent("text", {"content": "Hi"}),
                StreamEvent("done", {"success": False}),
            ]
        )
        service = SessionService(session_store=store, claude_runner=runner)

        session = await service.create_session(None, "/repo")

        async for _ in service.send_message(session.session_id, "Hello"):
            pass

        updated = await store.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "error"

    async def test_send_message_updates_status_on_error_event(self) -> None:
        """Error event updates status to error."""
        store = FakeSessionStore()
        runner = FakeClaudeRunner(
            default_response=[
                StreamEvent("error", {"message": "Something went wrong"}),
            ]
        )
        service = SessionService(session_store=store, claude_runner=runner)

        session = await service.create_session(None, "/repo")

        async for _ in service.send_message(session.session_id, "Hello"):
            pass

        updated = await store.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "error"

    async def test_send_message_passes_correct_params_to_runner(self) -> None:
        """Send message passes correct parameters to runner."""
        store = FakeSessionStore()
        runner = FakeClaudeRunner()
        service = SessionService(session_store=store, claude_runner=runner)

        session = await service.create_session(None, "/test/repo")

        async for _ in service.send_message(
            session.session_id, "Test message", timeout_seconds=120
        ):
            pass

        assert len(runner.execute_calls) == 1
        call = runner.execute_calls[0]
        assert call.session_id == session.session_id
        assert call.message == "Test message"
        assert call.working_directory == "/test/repo"
        assert call.timeout_seconds == 120


class TestSessionServiceGetOrCreate:
    """Tests for SessionService.get_or_create_session_by_external_id."""

    @pytest.fixture
    def service(self) -> SessionService:
        """Provide SessionService with fakes."""
        return SessionService(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(),
        )

    async def test_creates_new_session_if_not_exists(self, service: SessionService) -> None:
        """Creates new session if external ID not found."""
        result = await service.get_or_create_session_by_external_id("slack-new", "/new/repo")

        assert result.external_id == "slack-new"
        assert result.working_directory == "/new/repo"

    async def test_returns_existing_session_if_exists(self, service: SessionService) -> None:
        """Returns existing session if external ID found."""
        # Create first session
        first = await service.create_session("slack-existing", "/first/repo")

        # Get or create with same external ID
        result = await service.get_or_create_session_by_external_id(
            "slack-existing", "/different/repo"
        )

        assert result == first
        assert result.working_directory == "/first/repo"  # Original value

    async def test_creates_different_sessions_for_different_external_ids(
        self, service: SessionService
    ) -> None:
        """Different external IDs create different sessions."""
        session1 = await service.get_or_create_session_by_external_id("slack-1", "/repo")
        session2 = await service.get_or_create_session_by_external_id("slack-2", "/repo")

        assert session1.session_id != session2.session_id
        assert session1.external_id == "slack-1"
        assert session2.external_id == "slack-2"

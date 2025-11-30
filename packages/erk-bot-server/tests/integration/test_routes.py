"""Integration tests for FastAPI routes."""

import pytest
from erk_bot_server.context import ServerContext
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.main import create_app
from erk_bot_server.models.session import StreamEvent
from httpx import ASGITransport, AsyncClient


class TestSessionRoutes:
    """Tests for session management routes."""

    @pytest.fixture
    def fake_store(self) -> FakeSessionStore:
        """Provide a FakeSessionStore for testing."""
        return FakeSessionStore()

    @pytest.fixture
    def fake_runner(self) -> FakeClaudeRunner:
        """Provide a FakeClaudeRunner for testing."""
        return FakeClaudeRunner()

    @pytest.fixture
    def context(self, fake_store: FakeSessionStore, fake_runner: FakeClaudeRunner) -> ServerContext:
        """Provide a ServerContext for testing."""
        return ServerContext(session_store=fake_store, claude_runner=fake_runner)

    @pytest.fixture
    async def client(self, context: ServerContext) -> AsyncClient:
        """Provide an async HTTP client for testing."""
        app = create_app(context=context)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    async def test_create_session(self, client: AsyncClient) -> None:
        """POST /api/sessions creates a session."""
        response = await client.post(
            "/api/sessions",
            json={"working_directory": "/test/repo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["working_directory"] == "/test/repo"
        assert data["status"] == "active"

    async def test_create_session_with_external_id(self, client: AsyncClient) -> None:
        """POST /api/sessions with external_id stores it."""
        response = await client.post(
            "/api/sessions",
            json={
                "external_id": "slack-thread-123",
                "working_directory": "/test/repo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["external_id"] == "slack-thread-123"

    async def test_list_sessions_empty(self, client: AsyncClient) -> None:
        """GET /api/sessions returns empty list initially."""
        response = await client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    async def test_list_sessions_returns_all(self, client: AsyncClient) -> None:
        """GET /api/sessions returns all sessions."""
        # Create two sessions
        await client.post("/api/sessions", json={"working_directory": "/repo1"})
        await client.post("/api/sessions", json={"working_directory": "/repo2"})

        response = await client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2

    async def test_get_session(self, client: AsyncClient) -> None:
        """GET /api/sessions/{id} returns session info."""
        # Create a session
        create_response = await client.post(
            "/api/sessions",
            json={"working_directory": "/test/repo"},
        )
        session_id = create_response.json()["session_id"]

        response = await client.get(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["working_directory"] == "/test/repo"

    async def test_get_session_not_found(self, client: AsyncClient) -> None:
        """GET /api/sessions/{id} returns 404 for unknown session."""
        response = await client.get("/api/sessions/unknown-id")

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

    async def test_delete_session(self, client: AsyncClient) -> None:
        """DELETE /api/sessions/{id} deletes the session."""
        # Create a session
        create_response = await client.post(
            "/api/sessions",
            json={"working_directory": "/test/repo"},
        )
        session_id = create_response.json()["session_id"]

        response = await client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify it's deleted
        get_response = await client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 404

    async def test_delete_session_not_found(self, client: AsyncClient) -> None:
        """DELETE /api/sessions/{id} returns 404 for unknown session."""
        response = await client.delete("/api/sessions/unknown-id")

        assert response.status_code == 404


class TestMessageRoute:
    """Tests for the message streaming route."""

    @pytest.fixture
    def fake_store(self) -> FakeSessionStore:
        """Provide a FakeSessionStore for testing."""
        return FakeSessionStore()

    @pytest.fixture
    def fake_runner(self) -> FakeClaudeRunner:
        """Provide a FakeClaudeRunner with custom response."""
        return FakeClaudeRunner(
            default_response=[
                StreamEvent("text", {"content": "Hello from Claude!"}),
                StreamEvent("tool", {"name": "Read", "summary": "Reading file.py"}),
                StreamEvent("done", {"success": True}),
            ]
        )

    @pytest.fixture
    def context(self, fake_store: FakeSessionStore, fake_runner: FakeClaudeRunner) -> ServerContext:
        """Provide a ServerContext for testing."""
        return ServerContext(session_store=fake_store, claude_runner=fake_runner)

    @pytest.fixture
    async def client(self, context: ServerContext) -> AsyncClient:
        """Provide an async HTTP client for testing."""
        app = create_app(context=context)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    async def test_send_message_streams_events(
        self, client: AsyncClient, fake_runner: FakeClaudeRunner
    ) -> None:
        """POST /api/sessions/{id}/messages streams SSE events."""
        # Create a session
        create_response = await client.post(
            "/api/sessions",
            json={"working_directory": "/test/repo"},
        )
        session_id = create_response.json()["session_id"]

        # Send a message
        response = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "Help me with something"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse SSE response
        events = self._parse_sse(response.text)

        # Verify we got events and the last one is done
        assert len(events) >= 1
        # Find done event
        done_events = [e for e in events if e.get("event") == "done"]
        assert len(done_events) == 1
        assert '"success": true' in done_events[0].get("data", "")

        # Verify runner was called
        assert len(fake_runner.execute_calls) == 1
        call = fake_runner.execute_calls[0]
        assert call.session_id == session_id
        assert call.message == "Help me with something"
        assert call.working_directory == "/test/repo"

    async def test_send_message_to_unknown_session(self, client: AsyncClient) -> None:
        """POST /api/sessions/{id}/messages returns error for unknown session."""
        response = await client.post(
            "/api/sessions/unknown-id/messages",
            json={"content": "Hello"},
        )

        assert response.status_code == 200  # SSE always returns 200
        events = self._parse_sse(response.text)

        assert len(events) == 1
        assert events[0]["event"] == "error"

    def _parse_sse(self, text: str) -> list[dict[str, str]]:
        """Parse SSE response into list of events."""
        events = []
        current_event: dict[str, str] = {}

        for line in text.split("\n"):
            if line.startswith("event:"):
                current_event["event"] = line[6:].strip()
            elif line.startswith("data:"):
                current_event["data"] = line[5:].strip()
            elif line == "" and current_event:
                events.append(current_event)
                current_event = {}

        if current_event:
            events.append(current_event)

        return events

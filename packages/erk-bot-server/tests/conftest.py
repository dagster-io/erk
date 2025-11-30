"""Pytest fixtures for erk-bot-server tests."""

from datetime import datetime

import pytest
from erk_bot_server.context import ServerContext
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.models.session import StreamEvent
from erk_bot_server.services.session_service import SessionService


@pytest.fixture
def fixed_time() -> datetime:
    """Provide a fixed datetime for deterministic tests."""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def fake_session_store(fixed_time: datetime) -> FakeSessionStore:
    """Provide a FakeSessionStore for testing."""
    return FakeSessionStore(now=fixed_time)


@pytest.fixture
def fake_claude_runner() -> FakeClaudeRunner:
    """Provide a FakeClaudeRunner for testing."""
    return FakeClaudeRunner()


@pytest.fixture
def server_context(
    fake_session_store: FakeSessionStore,
    fake_claude_runner: FakeClaudeRunner,
) -> ServerContext:
    """Provide a ServerContext with fake implementations."""
    return ServerContext(
        session_store=fake_session_store,
        claude_runner=fake_claude_runner,
    )


@pytest.fixture
def session_service(
    fake_session_store: FakeSessionStore,
    fake_claude_runner: FakeClaudeRunner,
) -> SessionService:
    """Provide a SessionService with fake implementations."""
    return SessionService(
        session_store=fake_session_store,
        claude_runner=fake_claude_runner,
    )


@pytest.fixture
def sample_stream_events() -> list[StreamEvent]:
    """Provide sample stream events for testing."""
    return [
        StreamEvent("text", {"content": "Hello! I can help you with that."}),
        StreamEvent("tool", {"name": "Edit", "summary": "Editing foo.py"}),
        StreamEvent("text", {"content": "Done!"}),
        StreamEvent("done", {"success": True, "duration_seconds": 5}),
    ]

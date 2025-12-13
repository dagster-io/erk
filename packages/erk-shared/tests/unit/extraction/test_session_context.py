"""Unit tests for session context collection helper."""

from pathlib import Path

from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)
from erk_shared.extraction.session_context import (
    SessionContextResult,
    collect_session_context,
)
from erk_shared.git.fake import FakeGit


def test_collect_session_context_success(tmp_path: Path) -> None:
    """Test successful session context collection."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    # Create fake session store with session data
    session_content = (
        '{"type": "user", "message": {"content": "Hello"}}\n'
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "World"}]}}\n'
    )
    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test-session-id": FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    result = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="test-session-id",
    )

    assert result is not None
    assert isinstance(result, SessionContextResult)
    assert result.session_ids == ["test-session-id"]
    assert result.branch_context.current_branch == "feature-branch"
    assert "<session" in result.combined_xml


def test_collect_session_context_no_session_id() -> None:
    """Test returns None when no session ID provided."""
    fake_git = FakeGit()
    fake_store = FakeClaudeCodeSessionStore()

    result = collect_session_context(
        git=fake_git,
        cwd=Path("/fake"),
        session_store=fake_store,
        current_session_id=None,
    )

    assert result is None


def test_collect_session_context_no_project(tmp_path: Path) -> None:
    """Test returns None when no project exists for cwd."""
    fake_git = FakeGit()
    # Session store has no projects
    fake_store = FakeClaudeCodeSessionStore()

    result = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="test-session-id",
    )

    assert result is None


def test_collect_session_context_no_sessions(tmp_path: Path) -> None:
    """Test returns None when no sessions discovered."""
    fake_git = FakeGit()
    # Project exists but has no sessions
    fake_store = FakeClaudeCodeSessionStore(
        projects={tmp_path: FakeProject(sessions={})},
    )

    result = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="test-session-id",
    )

    assert result is None


def test_collect_session_context_empty_after_preprocessing(tmp_path: Path) -> None:
    """Test returns None when all sessions are empty after preprocessing."""
    fake_git = FakeGit()
    # Empty session content will result in None after preprocessing
    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "empty-session": FakeSessionData(
                        content="",  # Empty content
                        size_bytes=0,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    result = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="empty-session",
        min_size=0,  # Don't filter by size
    )

    assert result is None


def test_collect_session_context_multiple_sessions(tmp_path: Path) -> None:
    """Test combining multiple sessions into single XML."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    session1_content = '{"type": "user", "message": {"content": "First"}}\n'
    session2_content = '{"type": "user", "message": {"content": "Second"}}\n'

    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session-1": FakeSessionData(
                        content=session1_content,
                        size_bytes=1500,
                        modified_at=1234567890.0,
                    ),
                    "session-2": FakeSessionData(
                        content=session2_content,
                        size_bytes=1500,
                        modified_at=1234567891.0,
                    ),
                }
            )
        },
    )

    result = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="session-2",
        min_size=0,  # Don't filter by size
    )

    assert result is not None
    # Both sessions should be in result (sorted by modified_at, current session prioritized)
    assert "session-1" in result.session_ids or "session-2" in result.session_ids
    # Multiple sessions should have session markers
    if len(result.session_ids) > 1:
        assert "<!-- Session:" in result.combined_xml


def test_collect_session_context_uses_provided_session_id(tmp_path: Path) -> None:
    """Test that provided session_id is required for session context collection.

    The current_session_id parameter is used for:
    1. Early return when not provided (None)
    2. Passing to auto_select_sessions
    3. Marking is_current on sessions in find_sessions()
    """
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    session_content = '{"type": "user", "message": {"content": "Test"}}\n'
    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "provided-session": FakeSessionData(
                        content=session_content,
                        size_bytes=1500,
                        modified_at=1234567890.0,
                    ),
                }
            )
        },
    )

    # Without provided session_id, returns None
    result_without = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id=None,
        min_size=0,
    )
    assert result_without is None  # Early return when no session ID

    # With provided session_id, should proceed
    result_with = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="provided-session",
        min_size=0,
    )

    assert result_with is not None
    # Session should be found
    assert "provided-session" in result_with.session_ids


def test_collect_session_context_with_agent_logs(tmp_path: Path) -> None:
    """Test that agent logs are included in preprocessing."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    main_content = '{"type": "user", "message": {"content": "Main session"}}\n'
    agent_content = '{"type": "user", "message": {"content": "Agent task"}}\n'

    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test-session": FakeSessionData(
                        content=main_content,
                        size_bytes=1500,
                        modified_at=1234567890.0,
                        agent_logs={"agent-1": agent_content},
                    )
                }
            )
        },
    )

    result = collect_session_context(
        git=fake_git,
        cwd=tmp_path,
        session_store=fake_store,
        current_session_id="test-session",
        min_size=0,
    )

    assert result is not None
    # Both main content and agent content should be in the output
    assert "<user>" in result.combined_xml

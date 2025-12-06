"""Unit tests for session context collection helper."""

from pathlib import Path
from unittest.mock import patch

from erk_shared.extraction.session_context import (
    SessionContextResult,
    collect_session_context,
)
from erk_shared.extraction.types import BranchContext, SessionInfo
from erk_shared.git.fake import FakeGit


def test_collect_session_context_success(tmp_path: Path) -> None:
    """Test successful session context collection."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    # Create a session file
    project_dir = tmp_path / ".claude" / "projects" / "-test-project"
    project_dir.mkdir(parents=True)
    session_file = project_dir / "test-session-id.jsonl"
    session_file.write_text(
        '{"type": "user", "message": {"content": "Hello"}}\n'
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "World"}]}}\n',
        encoding="utf-8",
    )

    session_info = SessionInfo(
        session_id="test-session-id",
        path=session_file,
        size_bytes=2000,
        mtime_unix=1234567890.0,
        is_current=True,
    )
    branch_context = BranchContext(
        current_branch="feature-branch",
        trunk_branch="main",
        is_on_trunk=False,
    )

    with (
        patch(
            "erk_shared.extraction.session_context.get_current_session_id",
            return_value="test-session-id",
        ),
        patch(
            "erk_shared.extraction.session_context.find_project_dir",
            return_value=project_dir,
        ),
        patch(
            "erk_shared.extraction.session_context.get_branch_context",
            return_value=branch_context,
        ),
        patch(
            "erk_shared.extraction.session_context.discover_sessions",
            return_value=[session_info],
        ),
        patch(
            "erk_shared.extraction.session_context.auto_select_sessions",
            return_value=[session_info],
        ),
    ):
        result = collect_session_context(git=fake_git, cwd=tmp_path)

    assert result is not None
    assert isinstance(result, SessionContextResult)
    assert result.session_ids == ["test-session-id"]
    assert result.branch_context == branch_context
    assert "<session" in result.combined_xml


def test_collect_session_context_no_session_id() -> None:
    """Test returns None when no session ID available."""
    fake_git = FakeGit()

    with patch(
        "erk_shared.extraction.session_context.get_current_session_id",
        return_value=None,
    ):
        result = collect_session_context(git=fake_git, cwd=Path("/fake"))

    assert result is None


def test_collect_session_context_no_project_dir() -> None:
    """Test returns None when no project directory found."""
    fake_git = FakeGit()

    with (
        patch(
            "erk_shared.extraction.session_context.get_current_session_id",
            return_value="test-session-id",
        ),
        patch(
            "erk_shared.extraction.session_context.find_project_dir",
            return_value=None,
        ),
    ):
        result = collect_session_context(git=fake_git, cwd=Path("/fake"))

    assert result is None


def test_collect_session_context_no_sessions(tmp_path: Path) -> None:
    """Test returns None when no sessions discovered."""
    fake_git = FakeGit()
    project_dir = tmp_path / ".claude" / "projects"
    project_dir.mkdir(parents=True)

    branch_context = BranchContext(
        current_branch="main",
        trunk_branch="main",
        is_on_trunk=True,
    )

    with (
        patch(
            "erk_shared.extraction.session_context.get_current_session_id",
            return_value="test-session-id",
        ),
        patch(
            "erk_shared.extraction.session_context.find_project_dir",
            return_value=project_dir,
        ),
        patch(
            "erk_shared.extraction.session_context.get_branch_context",
            return_value=branch_context,
        ),
        patch(
            "erk_shared.extraction.session_context.discover_sessions",
            return_value=[],  # No sessions
        ),
    ):
        result = collect_session_context(git=fake_git, cwd=tmp_path)

    assert result is None


def test_collect_session_context_empty_after_preprocessing(tmp_path: Path) -> None:
    """Test returns None when all sessions are empty after preprocessing."""
    fake_git = FakeGit()
    project_dir = tmp_path / ".claude" / "projects"
    project_dir.mkdir(parents=True)

    # Create an empty session file
    session_file = project_dir / "empty-session.jsonl"
    session_file.write_text("", encoding="utf-8")

    session_info = SessionInfo(
        session_id="empty-session",
        path=session_file,
        size_bytes=0,
        mtime_unix=1234567890.0,
        is_current=True,
    )
    branch_context = BranchContext(
        current_branch="feature",
        trunk_branch="main",
        is_on_trunk=False,
    )

    with (
        patch(
            "erk_shared.extraction.session_context.get_current_session_id",
            return_value="empty-session",
        ),
        patch(
            "erk_shared.extraction.session_context.find_project_dir",
            return_value=project_dir,
        ),
        patch(
            "erk_shared.extraction.session_context.get_branch_context",
            return_value=branch_context,
        ),
        patch(
            "erk_shared.extraction.session_context.discover_sessions",
            return_value=[session_info],
        ),
        patch(
            "erk_shared.extraction.session_context.auto_select_sessions",
            return_value=[session_info],
        ),
        patch(
            "erk_shared.extraction.session_context.preprocess_session",
            return_value=None,  # Empty after preprocessing
        ),
    ):
        result = collect_session_context(git=fake_git, cwd=tmp_path)

    assert result is None


def test_collect_session_context_multiple_sessions(tmp_path: Path) -> None:
    """Test combining multiple sessions into single XML."""
    fake_git = FakeGit()
    project_dir = tmp_path / ".claude" / "projects"
    project_dir.mkdir(parents=True)

    # Create two session files
    session_file1 = project_dir / "session-1.jsonl"
    session_file1.write_text(
        '{"type": "user", "message": {"content": "First"}}\n', encoding="utf-8"
    )
    session_file2 = project_dir / "session-2.jsonl"
    session_file2.write_text(
        '{"type": "user", "message": {"content": "Second"}}\n', encoding="utf-8"
    )

    session_info1 = SessionInfo(
        session_id="session-1",
        path=session_file1,
        size_bytes=1500,
        mtime_unix=1234567890.0,
        is_current=False,
    )
    session_info2 = SessionInfo(
        session_id="session-2",
        path=session_file2,
        size_bytes=1500,
        mtime_unix=1234567891.0,
        is_current=True,
    )
    branch_context = BranchContext(
        current_branch="feature",
        trunk_branch="main",
        is_on_trunk=False,
    )

    with (
        patch(
            "erk_shared.extraction.session_context.get_current_session_id",
            return_value="session-2",
        ),
        patch(
            "erk_shared.extraction.session_context.find_project_dir",
            return_value=project_dir,
        ),
        patch(
            "erk_shared.extraction.session_context.get_branch_context",
            return_value=branch_context,
        ),
        patch(
            "erk_shared.extraction.session_context.discover_sessions",
            return_value=[session_info1, session_info2],
        ),
        patch(
            "erk_shared.extraction.session_context.auto_select_sessions",
            return_value=[session_info1, session_info2],  # Both selected
        ),
    ):
        result = collect_session_context(git=fake_git, cwd=tmp_path)

    assert result is not None
    assert result.session_ids == ["session-1", "session-2"]
    # Multiple sessions should have session markers
    assert "<!-- Session: session-1 -->" in result.combined_xml
    assert "<!-- Session: session-2 -->" in result.combined_xml


def test_collect_session_context_uses_provided_session_id(tmp_path: Path) -> None:
    """Test that provided session_id is used instead of auto-detecting."""
    fake_git = FakeGit()
    project_dir = tmp_path / ".claude" / "projects"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "provided-session.jsonl"
    session_file.write_text('{"type": "user", "message": {"content": "Test"}}\n', encoding="utf-8")

    session_info = SessionInfo(
        session_id="provided-session",
        path=session_file,
        size_bytes=1500,
        mtime_unix=1234567890.0,
        is_current=True,
    )
    branch_context = BranchContext(
        current_branch="feature",
        trunk_branch="main",
        is_on_trunk=False,
    )

    with (
        patch(
            "erk_shared.extraction.session_context.find_project_dir",
            return_value=project_dir,
        ),
        patch(
            "erk_shared.extraction.session_context.get_branch_context",
            return_value=branch_context,
        ),
        patch(
            "erk_shared.extraction.session_context.discover_sessions",
            return_value=[session_info],
        ) as mock_discover,
        patch(
            "erk_shared.extraction.session_context.auto_select_sessions",
            return_value=[session_info],
        ),
    ):
        # Provide explicit session_id
        result = collect_session_context(
            git=fake_git,
            cwd=tmp_path,
            current_session_id="provided-session",
        )

    assert result is not None
    # Verify discover_sessions was called with the provided session_id
    mock_discover.assert_called_once()
    call_kwargs = mock_discover.call_args[1]
    assert call_kwargs["current_session_id"] == "provided-session"

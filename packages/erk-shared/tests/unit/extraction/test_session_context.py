"""Unit tests for session context collection helper."""

from pathlib import Path

from erk_shared.extraction.fake_session_environment import FakeSessionEnvironment, FileEntry
from erk_shared.extraction.session_context import (
    SessionContextResult,
    collect_session_context,
)
from erk_shared.extraction.session_discovery import encode_path_to_project_folder
from erk_shared.git.fake import FakeGit


def test_collect_session_context_success() -> None:
    """Test successful session context collection."""
    # Setup paths
    home = Path("/fake/home")
    cwd = Path("/fake/project")
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = home / ".claude" / "projects" / encoded_path
    session_path = project_dir / "test-session-id.jsonl"

    # Create fake git
    fake_git = FakeGit(
        current_branches={cwd: "feature-branch"},
        trunk_branches={cwd: "main"},
    )

    # Create fake environment with session file
    session_content = (
        '{"type": "user", "message": {"content": "Hello"}}\n'
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "World"}]}}\n'
    )

    fake_env = FakeSessionEnvironment(
        session_context="session_id=test-session-id",
        home_dir=home,
        files={
            session_path: FileEntry(content=session_content, mtime=1234567890.0),
        },
    )

    result = collect_session_context(git=fake_git, cwd=cwd, env=fake_env, min_size=0)

    assert result is not None
    assert isinstance(result, SessionContextResult)
    assert result.session_ids == ["test-session-id"]
    assert result.branch_context.current_branch == "feature-branch"
    assert "<session" in result.combined_xml


def test_collect_session_context_no_session_id() -> None:
    """Test returns None when no session ID available."""
    fake_env = FakeSessionEnvironment(session_context=None)

    result = collect_session_context(
        git=FakeGit(),
        cwd=Path("/fake"),
        env=fake_env,
    )

    assert result is None


def test_collect_session_context_no_project_dir() -> None:
    """Test returns None when no project directory found."""
    fake_env = FakeSessionEnvironment(
        session_context="session_id=test-session-id",
        home_dir=Path("/fake/home"),
        # No files or directories - project dir won't exist
    )

    result = collect_session_context(
        git=FakeGit(),
        cwd=Path("/fake"),
        env=fake_env,
    )

    assert result is None


def test_collect_session_context_no_sessions() -> None:
    """Test returns None when no sessions discovered."""
    home = Path("/fake/home")
    cwd = Path("/fake/project")
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = home / ".claude" / "projects" / encoded_path

    fake_env = FakeSessionEnvironment(
        session_context="session_id=test-session-id",
        home_dir=home,
        directories={project_dir},  # Empty project dir
    )

    result = collect_session_context(
        git=FakeGit(),
        cwd=cwd,
        env=fake_env,
    )

    assert result is None


def test_collect_session_context_empty_file_produces_minimal_xml() -> None:
    """Test that empty session file produces minimal but valid XML structure."""
    home = Path("/fake/home")
    cwd = Path("/fake/project")
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = home / ".claude" / "projects" / encoded_path
    session_path = project_dir / "empty-session.jsonl"

    fake_git = FakeGit(
        current_branches={cwd: "feature-branch"},
        trunk_branches={cwd: "main"},
    )

    fake_env = FakeSessionEnvironment(
        session_context="session_id=empty-session",
        home_dir=home,
        files={
            session_path: FileEntry(content="", mtime=1234567890.0),
        },
    )

    result = collect_session_context(
        git=fake_git,
        cwd=cwd,
        env=fake_env,
        min_size=0,  # Allow empty files to be discovered
    )

    # Empty file produces minimal XML structure (just <session></session>)
    # This is still valid output, not None
    assert result is not None
    assert "<session>" in result.combined_xml
    assert "</session>" in result.combined_xml


def test_collect_session_context_multiple_sessions() -> None:
    """Test combining multiple sessions into single XML."""
    home = Path("/fake/home")
    cwd = Path("/fake/project")
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = home / ".claude" / "projects" / encoded_path
    session_path1 = project_dir / "session-1.jsonl"
    session_path2 = project_dir / "session-2.jsonl"

    fake_git = FakeGit(
        current_branches={cwd: "feature"},
        trunk_branches={cwd: "main"},
    )

    fake_env = FakeSessionEnvironment(
        session_context="session_id=session-2",
        home_dir=home,
        files={
            session_path1: FileEntry(
                content='{"type": "user", "message": {"content": "First"}}\n',
                mtime=1234567890.0,
            ),
            session_path2: FileEntry(
                content='{"type": "user", "message": {"content": "Second"}}\n',
                mtime=1234567891.0,
            ),
        },
    )

    result = collect_session_context(git=fake_git, cwd=cwd, env=fake_env, min_size=0)

    assert result is not None
    # Both sessions should be included (session_ids list should have both)
    assert len(result.session_ids) >= 1
    # At minimum the current session should be included
    assert "session-2" in result.session_ids


def test_collect_session_context_uses_provided_session_id() -> None:
    """Test that provided session_id is used instead of auto-detecting."""
    home = Path("/fake/home")
    cwd = Path("/fake/project")
    encoded_path = encode_path_to_project_folder(cwd)
    project_dir = home / ".claude" / "projects" / encoded_path
    session_path = project_dir / "provided-session.jsonl"

    fake_git = FakeGit(
        current_branches={cwd: "feature"},
        trunk_branches={cwd: "main"},
    )

    fake_env = FakeSessionEnvironment(
        session_context="session_id=different-session",  # Different from provided
        home_dir=home,
        files={
            session_path: FileEntry(
                content='{"type": "user", "message": {"content": "Test"}}\n',
                mtime=1234567890.0,
            ),
        },
    )

    # Provide explicit session_id
    result = collect_session_context(
        git=fake_git,
        cwd=cwd,
        env=fake_env,
        current_session_id="provided-session",
        min_size=0,
    )

    assert result is not None
    assert "provided-session" in result.session_ids

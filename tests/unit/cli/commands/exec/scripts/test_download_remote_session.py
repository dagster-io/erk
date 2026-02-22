"""Unit tests for download-remote-session exec script.

Tests downloading session files from git branches.
Uses FakeGit injected into _execute_download for git operations.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.download_remote_session import (
    _execute_download,
    _get_remote_sessions_dir,
)
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session as download_remote_session_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit

# ============================================================================
# 1. Helper Function Tests (2 tests)
# ============================================================================


def test_get_remote_sessions_dir_creates_directory(tmp_path: Path) -> None:
    """Test that the remote sessions directory is created if it doesn't exist."""
    session_id = "test-session-123"

    result = _get_remote_sessions_dir(tmp_path, session_id)

    expected = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    assert result == expected
    assert result.exists()
    assert result.is_dir()


def test_get_remote_sessions_dir_returns_existing(tmp_path: Path) -> None:
    """Test that existing directory is returned without error."""
    session_id = "existing-session"
    expected = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    expected.mkdir(parents=True)

    result = _get_remote_sessions_dir(tmp_path, session_id)

    assert result == expected


# ============================================================================
# 2. CLI Argument Validation Tests (2 tests)
# ============================================================================


def test_cli_missing_session_branch() -> None:
    """Test CLI requires --session-branch option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--session-id", "test-123"],
        obj=ErkContext.for_test(),
    )

    assert result.exit_code != 0
    assert "session-branch" in result.output.lower() or "missing" in result.output.lower()


def test_cli_missing_session_id() -> None:
    """Test CLI requires --session-id option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--session-branch", "async-learn/42"],
        obj=ErkContext.for_test(),
    )

    assert result.exit_code != 0
    assert "session-id" in result.output.lower() or "missing" in result.output.lower()


# ============================================================================
# 3. Core Logic Tests (2 tests) — call _execute_download with FakeGit
# ============================================================================


def test_error_download_fails_when_branch_not_found(tmp_path: Path) -> None:
    """Test error when git show fails to extract session from branch.

    tmp_path is not a git repository, so subprocess git show returns non-zero.
    The FakeGit records the fetch_branch call but does not make real git calls.
    """
    fake_git = FakeGit(current_branches={tmp_path: "main"})

    exit_code, output = _execute_download(
        repo_root=tmp_path,
        session_branch="async-learn/42",
        session_id="test-session-123",
        git=fake_git,
    )

    assert exit_code == 1
    assert output["success"] is False
    assert "Failed to extract session from branch" in str(output["error"])

    # Verify fetch was attempted via FakeGit
    assert ("origin", "async-learn/42") in fake_git.fetched_branches


def test_cleanup_existing_directory_on_redownload(tmp_path: Path) -> None:
    """Test that existing directory contents are cleaned up before download attempt."""
    session_id = "redownload-session"
    fake_git = FakeGit(current_branches={tmp_path: "main"})

    # Pre-create the session directory with old files
    session_dir = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    session_dir.mkdir(parents=True)
    old_file = session_dir / "old-session.jsonl"
    old_file.write_text('{"old": true}\n', encoding="utf-8")

    # Download attempt (will fail since tmp_path is not a git repo)
    exit_code, _output = _execute_download(
        repo_root=tmp_path,
        session_branch="async-learn/42",
        session_id=session_id,
        git=fake_git,
    )

    # Old file should be cleaned up even though download failed
    assert not old_file.exists(), "Old file should be cleaned up before download attempt"
    # Download fails because tmp_path is not a git repo
    assert exit_code == 1

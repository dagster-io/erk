"""Unit tests for git_lock_check_hook command.

These tests use ErkContext.for_test() injection. The .erk/ directory
is created in tmp_path to mark it as a managed project.
"""

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.git_lock_check_hook import (
    git_lock_check_hook,
    is_stale_lock,
)
from erk_shared.context.context import ErkContext


class TestIsStaleLock:
    """Tests for the is_stale_lock pure function."""

    def test_zero_bytes_is_stale(self) -> None:
        """0-byte lock file is considered stale."""
        assert is_stale_lock(0) is True

    def test_nonzero_bytes_not_stale(self) -> None:
        """Non-zero byte lock file is not considered stale."""
        assert is_stale_lock(1) is False
        assert is_stale_lock(100) is False
        assert is_stale_lock(4096) is False


def _get_lock_path(git_repo: Path) -> Path:
    """Get the absolute lock path for a git repo.

    git rev-parse returns paths relative to the repo root, so we need to
    resolve them to absolute paths for the tests to work correctly.
    """
    result = subprocess.run(
        ["git", "-C", str(git_repo), "rev-parse", "--git-path", "index.lock"],
        capture_output=True,
        text=True,
        check=True,
    )
    lock_path_str = result.stdout.strip()
    # git rev-parse returns paths relative to repo root
    if Path(lock_path_str).is_absolute():
        return Path(lock_path_str)
    return git_repo / lock_path_str


class TestGitLockCheckHook:
    """Tests for the git_lock_check_hook command."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a git repository in tmp_path."""
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()
        return tmp_path

    def test_cleans_stale_zero_byte_lock(self, git_repo: Path) -> None:
        """Test that hook cleans a 0-byte (stale) lock file."""
        runner = CliRunner()

        lock_path = _get_lock_path(git_repo)

        # Create a 0-byte lock file (stale)
        lock_path.touch()
        assert lock_path.exists()
        assert lock_path.stat().st_size == 0

        # Inject via ErkContext
        ctx = ErkContext.for_test(repo_root=git_repo, cwd=git_repo)
        result = runner.invoke(git_lock_check_hook, input="", obj=ctx)

        assert result.exit_code == 0
        assert not lock_path.exists(), "Stale lock should have been cleaned"
        assert "Cleaned stale git index.lock" in result.output

    def test_leaves_active_lock_intact(self, git_repo: Path) -> None:
        """Test that hook leaves a non-zero byte (active) lock file alone."""
        runner = CliRunner()

        lock_path = _get_lock_path(git_repo)

        # Create a non-zero byte lock file (active)
        lock_path.write_text("active lock content", encoding="utf-8")
        assert lock_path.exists()
        assert lock_path.stat().st_size > 0

        # Inject via ErkContext
        ctx = ErkContext.for_test(repo_root=git_repo, cwd=git_repo)
        result = runner.invoke(git_lock_check_hook, input="", obj=ctx)

        assert result.exit_code == 0
        assert lock_path.exists(), "Active lock should not be deleted"
        assert "Cleaned stale" not in result.output

    def test_no_lock_file_exits_cleanly(self, git_repo: Path) -> None:
        """Test that hook exits cleanly when no lock file exists."""
        runner = CliRunner()

        # Inject via ErkContext
        ctx = ErkContext.for_test(repo_root=git_repo, cwd=git_repo)
        result = runner.invoke(git_lock_check_hook, input="", obj=ctx)

        assert result.exit_code == 0
        assert "Cleaned stale" not in result.output

    def test_non_erk_project_exits_cleanly(self, tmp_path: Path) -> None:
        """Test that hook exits cleanly when not in an erk project."""
        runner = CliRunner()

        # Initialize a git repo but do NOT create .erk/
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create a stale lock file
        lock_path = _get_lock_path(tmp_path)
        lock_path.touch()

        # Inject via ErkContext (no .erk/ directory)
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        result = runner.invoke(git_lock_check_hook, input="", obj=ctx)

        assert result.exit_code == 0
        # Lock should still exist - hook doesn't run for non-erk projects
        assert lock_path.exists()

    def test_not_a_git_repo_exits_cleanly(self, tmp_path: Path) -> None:
        """Test that hook exits cleanly when not in a git repo."""
        runner = CliRunner()

        # Create .erk/ to mark as managed project, but no git repo
        (tmp_path / ".erk").mkdir()

        # Inject via ErkContext
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        result = runner.invoke(git_lock_check_hook, input="", obj=ctx)

        assert result.exit_code == 0
        assert "Cleaned stale" not in result.output

    def test_with_session_id_from_stdin(self, git_repo: Path) -> None:
        """Test that hook works correctly with session ID from stdin."""
        runner = CliRunner()
        stdin_data = json.dumps({"session_id": "test-session-123"})

        lock_path = _get_lock_path(git_repo)
        lock_path.touch()

        # Inject via ErkContext
        ctx = ErkContext.for_test(repo_root=git_repo, cwd=git_repo)
        result = runner.invoke(git_lock_check_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert not lock_path.exists()

"""Unit tests for commit_and_push_if_dirty kit CLI command.

Tests conditional commit and push based on working directory state.
Uses FakeGit for dependency injection instead of mocking subprocess.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit

from dot_agent_kit.data.kits.erk.scripts.erk.commit_and_push_if_dirty import (
    CommitSuccess,
    NoChanges,
    _commit_and_push_if_dirty_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.commit_and_push_if_dirty import (
    commit_and_push_if_dirty as commit_and_push_if_dirty_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    git: Git
    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_commits_when_dirty(tmp_path: Path) -> None:
    """Test that changes are committed and pushed when dirty."""
    git = FakeGit(
        file_statuses={tmp_path: ([], ["modified.txt"], [])},  # Has modified files
        branch_heads={"HEAD": "abc1234567890"},
    )

    result = _commit_and_push_if_dirty_impl(git, tmp_path, "feature", "Update files")

    assert isinstance(result, CommitSuccess)
    assert result.success is True
    assert result.committed is True
    assert result.sha == "abc1234"

    # Verify git operations
    assert len(git.commits) == 1
    assert git.commits[0][1] == "Update files"
    assert ("origin", "feature", False) in git.pushed_branches


def test_impl_no_commit_when_clean(tmp_path: Path) -> None:
    """Test that no commit is made when working directory is clean."""
    git = FakeGit()  # No dirty_worktrees = clean

    result = _commit_and_push_if_dirty_impl(git, tmp_path, "feature", "Update files")

    assert isinstance(result, NoChanges)
    assert result.success is True
    assert result.committed is False
    assert "No changes" in result.message

    # Verify no git operations
    assert len(git.commits) == 0
    assert len(git.pushed_branches) == 0


def test_impl_stages_all_changes(tmp_path: Path) -> None:
    """Test that all changes are staged before commit."""
    git = FakeGit(
        file_statuses={tmp_path: ([], ["modified.txt"], [])},
        branch_heads={"HEAD": "def456"},
    )

    _commit_and_push_if_dirty_impl(git, tmp_path, "feature", "Update")

    # Verify commit was made (proves add_all was called since commit needs staged files)
    assert len(git.commits) == 1


def test_impl_handles_missing_sha(tmp_path: Path) -> None:
    """Test handling when HEAD sha cannot be retrieved."""
    git = FakeGit(
        file_statuses={tmp_path: ([], ["modified.txt"], [])},
        # No branch_heads configured - get_branch_head returns None
    )

    result = _commit_and_push_if_dirty_impl(git, tmp_path, "feature", "Update")

    assert isinstance(result, CommitSuccess)
    assert result.sha == "unknown"


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_commits_dirty(tmp_path: Path) -> None:
    """Test CLI when working directory is dirty."""
    runner = CliRunner()
    git = FakeGit(
        file_statuses={tmp_path: ([], ["modified.txt"], [])},
        branch_heads={"HEAD": "abc123"},
    )
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(
        commit_and_push_if_dirty_command,
        ["--branch", "feature", "--message", "Update files"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["committed"] is True


def test_cli_no_changes(tmp_path: Path) -> None:
    """Test CLI when working directory is clean."""
    runner = CliRunner()
    git = FakeGit()
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(
        commit_and_push_if_dirty_command,
        ["--branch", "feature", "--message", "Update files"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["committed"] is False


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    git = FakeGit(
        file_statuses={tmp_path: ([], ["modified.txt"], [])},
        branch_heads={"HEAD": "abc123"},
    )
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(
        commit_and_push_if_dirty_command,
        ["--branch", "feature", "--message", "Update"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys for committed result
    assert "success" in output
    assert "committed" in output
    assert "sha" in output

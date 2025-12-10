"""Unit tests for trigger_ci_push kit CLI command.

Tests creating empty commits and pushing to trigger CI workflows.
Uses FakeGit for dependency injection instead of mocking subprocess.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit

from dot_agent_kit.data.kits.erk.scripts.erk.trigger_ci_push import (
    TriggerSuccess,
    _trigger_ci_push_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.trigger_ci_push import (
    trigger_ci_push as trigger_ci_push_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    git: Git
    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (3 tests)
# ============================================================================


def test_impl_creates_empty_commit(tmp_path: Path) -> None:
    """Test that empty commit is created and pushed."""
    git = FakeGit(branch_heads={"HEAD": "abc1234567890"})

    result = _trigger_ci_push_impl(git, tmp_path, "feature", "Trigger CI")

    assert isinstance(result, TriggerSuccess)
    assert result.success is True
    assert result.sha == "abc1234"

    # Verify git operations
    assert len(git.commits) == 1
    assert git.commits[0][1] == "Trigger CI"
    assert ("origin", "feature", False) in git.pushed_branches


def test_impl_handles_missing_sha(tmp_path: Path) -> None:
    """Test handling when HEAD sha cannot be retrieved."""
    git = FakeGit()  # No branch_heads configured

    result = _trigger_ci_push_impl(git, tmp_path, "feature", "Trigger CI")

    assert isinstance(result, TriggerSuccess)
    assert result.sha == "unknown"


def test_impl_pushes_to_correct_branch(tmp_path: Path) -> None:
    """Test that push is made to the specified branch."""
    git = FakeGit(branch_heads={"HEAD": "def456"})

    _trigger_ci_push_impl(git, tmp_path, "my-branch", "Trigger CI")

    # Verify push was to correct branch
    assert len(git.pushed_branches) == 1
    assert git.pushed_branches[0] == ("origin", "my-branch", False)


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI creates empty commit and pushes."""
    runner = CliRunner()
    git = FakeGit(branch_heads={"HEAD": "abc123"})
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(
        trigger_ci_push_command,
        ["--branch", "feature", "--message", "Trigger CI workflows"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "sha" in output


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    git = FakeGit(branch_heads={"HEAD": "abc123"})
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(
        trigger_ci_push_command,
        ["--branch", "feature", "--message", "Trigger CI"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "sha" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["sha"], str)


def test_cli_requires_options(tmp_path: Path) -> None:
    """Test that CLI requires both --branch and --message."""
    runner = CliRunner()
    git = FakeGit()
    ctx = CLIContext(git=git, cwd=tmp_path)

    # Missing --message
    result = runner.invoke(
        trigger_ci_push_command,
        ["--branch", "feature"],
        obj=ctx,
    )
    assert result.exit_code != 0

    # Missing --branch
    result = runner.invoke(
        trigger_ci_push_command,
        ["--message", "Trigger CI"],
        obj=ctx,
    )
    assert result.exit_code != 0

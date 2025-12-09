"""Unit tests for detect_trunk_branch kit CLI command.

Tests detection of trunk branch (main or master) by querying remote.
Uses FakeGit for dependency injection instead of mocking subprocess.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit

from dot_agent_kit.data.kits.erk.scripts.erk.detect_trunk_branch import (
    DetectedTrunk,
    DetectionError,
    _detect_trunk_branch_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.detect_trunk_branch import (
    detect_trunk_branch as detect_trunk_branch_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    git: Git
    repo_root: Path


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_detect_impl_main_found(tmp_path: Path) -> None:
    """Test detection when main branch exists on remote."""
    git = FakeGit(remote_branches={tmp_path: ["origin/main"]})

    result = _detect_trunk_branch_impl(git, tmp_path)

    assert isinstance(result, DetectedTrunk)
    assert result.success is True
    assert result.trunk_branch == "main"


def test_detect_impl_master_found(tmp_path: Path) -> None:
    """Test detection when only master branch exists on remote."""
    git = FakeGit(remote_branches={tmp_path: ["origin/master"]})

    result = _detect_trunk_branch_impl(git, tmp_path)

    assert isinstance(result, DetectedTrunk)
    assert result.success is True
    assert result.trunk_branch == "master"


def test_detect_impl_main_preferred_over_master(tmp_path: Path) -> None:
    """Test that main is preferred when both exist on remote."""
    git = FakeGit(remote_branches={tmp_path: ["origin/main", "origin/master"]})

    result = _detect_trunk_branch_impl(git, tmp_path)

    assert isinstance(result, DetectedTrunk)
    assert result.success is True
    assert result.trunk_branch == "main"


def test_detect_impl_neither_found(tmp_path: Path) -> None:
    """Test error when neither main nor master exists on remote."""
    git = FakeGit(remote_branches={tmp_path: []})

    result = _detect_trunk_branch_impl(git, tmp_path)

    assert isinstance(result, DetectionError)
    assert result.success is False
    assert result.error == "trunk_not_found"
    assert "main" in result.message
    assert "master" in result.message


# ============================================================================
# 2. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success_main(tmp_path: Path) -> None:
    """Test CLI command when main branch detected."""
    runner = CliRunner()
    git = FakeGit(remote_branches={tmp_path: ["origin/main"]})
    ctx = CLIContext(git=git, repo_root=tmp_path)

    result = runner.invoke(detect_trunk_branch_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["trunk_branch"] == "main"


def test_cli_success_master(tmp_path: Path) -> None:
    """Test CLI command when master branch detected."""
    runner = CliRunner()
    git = FakeGit(remote_branches={tmp_path: ["origin/master"]})
    ctx = CLIContext(git=git, repo_root=tmp_path)

    result = runner.invoke(detect_trunk_branch_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["trunk_branch"] == "master"


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI command exits with error code when no trunk found."""
    runner = CliRunner()
    git = FakeGit(remote_branches={tmp_path: []})
    ctx = CLIContext(git=git, repo_root=tmp_path)

    result = runner.invoke(detect_trunk_branch_command, [], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "trunk_not_found"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    runner = CliRunner()
    git = FakeGit(remote_branches={tmp_path: ["origin/main"]})
    ctx = CLIContext(git=git, repo_root=tmp_path)

    result = runner.invoke(detect_trunk_branch_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "trunk_branch" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["trunk_branch"], str)

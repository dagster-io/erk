"""Unit tests for configure_git_user kit CLI command.

Tests setting git user identity from a GitHub username.
Uses FakeGit for dependency injection instead of mocking subprocess.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit

from dot_agent_kit.data.kits.erk.scripts.erk.configure_git_user import (
    ConfigureError,
    ConfigureSuccess,
    _configure_git_user_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.configure_git_user import (
    configure_git_user as configure_git_user_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    git: Git
    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (3 tests)
# ============================================================================


def test_impl_configures_user(tmp_path: Path) -> None:
    """Test successful configuration of git user."""
    git = FakeGit()

    result = _configure_git_user_impl(git, tmp_path, "octocat")

    assert isinstance(result, ConfigureSuccess)
    assert result.success is True
    assert result.user_name == "octocat"
    assert result.user_email == "octocat@users.noreply.github.com"

    # Verify git config was called correctly
    assert len(git.config_settings) == 2
    assert (tmp_path, "user.name", "octocat") in git.config_settings
    assert (tmp_path, "user.email", "octocat@users.noreply.github.com") in git.config_settings


def test_impl_strips_whitespace(tmp_path: Path) -> None:
    """Test that username whitespace is stripped."""
    git = FakeGit()

    result = _configure_git_user_impl(git, tmp_path, "  octocat  ")

    assert isinstance(result, ConfigureSuccess)
    assert result.user_name == "octocat"
    assert result.user_email == "octocat@users.noreply.github.com"


def test_impl_rejects_empty_username(tmp_path: Path) -> None:
    """Test error with empty username."""
    git = FakeGit()

    result = _configure_git_user_impl(git, tmp_path, "")

    assert isinstance(result, ConfigureError)
    assert result.success is False
    assert result.error == "invalid_username"


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command with valid username."""
    runner = CliRunner()
    git = FakeGit()
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, ["--username", "octocat"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["user_name"] == "octocat"
    assert output["user_email"] == "octocat@users.noreply.github.com"


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI exits with error code on invalid username."""
    runner = CliRunner()
    git = FakeGit()
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, ["--username", "  "], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_username"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    runner = CliRunner()
    git = FakeGit()
    ctx = CLIContext(git=git, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, ["--username", "octocat"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "user_name" in output
    assert "user_email" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["user_name"], str)
    assert isinstance(output["user_email"], str)

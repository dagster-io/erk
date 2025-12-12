"""Unit tests for configure_git_user kit CLI command.

Tests configuration of git user identity from GitHub username.
Uses FakeGit and FakeGitHub for dependency injection instead of mocking subprocess.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.configure_git_user import (
    ConfigurationError,
    ConfiguredUser,
    _configure_git_user_impl,
)
from erk_kits.data.kits.erk.scripts.erk.configure_git_user import (
    configure_git_user as configure_git_user_command,
)
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    git: Git
    github: GitHub
    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_success(tmp_path: Path) -> None:
    """Test successful configuration when authenticated."""
    git = FakeGit()
    github = FakeGitHub(authenticated=True, auth_username="octocat")

    result = _configure_git_user_impl(git, github, tmp_path)

    assert isinstance(result, ConfiguredUser)
    assert result.success is True
    assert result.username == "octocat"
    assert result.email == "octocat@users.noreply.github.com"


def test_impl_sets_git_config(tmp_path: Path) -> None:
    """Test that git config is actually set."""
    git = FakeGit()
    github = FakeGitHub(authenticated=True, auth_username="testuser")

    _configure_git_user_impl(git, github, tmp_path)

    # Verify git config was called with correct values
    assert len(git.config_settings) == 2
    assert ("user.name", "testuser", "local") in git.config_settings
    assert ("user.email", "testuser@users.noreply.github.com", "local") in git.config_settings


def test_impl_not_authenticated(tmp_path: Path) -> None:
    """Test error when not authenticated."""
    git = FakeGit()
    github = FakeGitHub(authenticated=False)

    result = _configure_git_user_impl(git, github, tmp_path)

    assert isinstance(result, ConfigurationError)
    assert result.success is False
    assert result.error == "not_authenticated"
    assert "gh auth login" in result.message


def test_impl_no_username(tmp_path: Path) -> None:
    """Test error when authenticated but username is None."""
    git = FakeGit()
    # Note: auth_username defaults to None when not explicitly set
    github = FakeGitHub(authenticated=True, auth_username=None)

    result = _configure_git_user_impl(git, github, tmp_path)

    assert isinstance(result, ConfigurationError)
    assert result.success is False
    assert result.error == "not_authenticated"


# ============================================================================
# 2. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command when authenticated."""
    runner = CliRunner()
    git = FakeGit()
    github = FakeGitHub(authenticated=True, auth_username="octocat")
    ctx = CLIContext(git=git, github=github, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["username"] == "octocat"
    assert output["email"] == "octocat@users.noreply.github.com"


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI command exits with error code when not authenticated."""
    runner = CliRunner()
    git = FakeGit()
    github = FakeGitHub(authenticated=False)
    ctx = CLIContext(git=git, github=github, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, [], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "not_authenticated"


def test_cli_json_output_structure_success(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    runner = CliRunner()
    git = FakeGit()
    github = FakeGitHub(authenticated=True, auth_username="testuser")
    ctx = CLIContext(git=git, github=github, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "username" in output
    assert "email" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["username"], str)
    assert isinstance(output["email"], str)


def test_cli_json_output_structure_error(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on error."""
    runner = CliRunner()
    git = FakeGit()
    github = FakeGitHub(authenticated=False)
    ctx = CLIContext(git=git, github=github, cwd=tmp_path)

    result = runner.invoke(configure_git_user_command, [], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)

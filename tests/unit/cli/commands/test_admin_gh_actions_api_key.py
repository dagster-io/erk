"""Unit tests for admin gh-actions-api-key command."""

import os
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env

# --- Status display tests ---


def test_status_enabled() -> None:
    """Display mode shows Enabled when ANTHROPIC_API_KEY secret exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Enabled" in result.output


def test_status_not_found() -> None:
    """Display mode shows Not found when secret does not exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Not found" in result.output


def test_status_api_error() -> None:
    """Display mode shows Error when secret_exists returns None."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secret_check_error=True)
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Error" in result.output


# --- Enable tests ---


def test_enable_sets_secret() -> None:
    """--enable reads local env var and sets GitHub Actions secret."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-123"}):
            result = runner.invoke(cli, ["admin", "gh-actions-api-key", "--enable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set ANTHROPIC_API_KEY" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "ANTHROPIC_API_KEY"
        assert value == "sk-test-123"


def test_enable_errors_without_env_var() -> None:
    """--enable fails when ANTHROPIC_API_KEY is not in local environment."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {}, clear=False):
            # Ensure ANTHROPIC_API_KEY is not set
            env_copy = dict(**os.environ)
            env_copy.pop("ANTHROPIC_API_KEY", None)
            with patch.dict("os.environ", env_copy, clear=True):
                result = runner.invoke(
                    cli, ["admin", "gh-actions-api-key", "--enable"], obj=ctx
                )

        assert result.exit_code == 1
        assert "not found in local environment" in result.output
        assert len(admin.set_secret_calls) == 0


# --- Disable tests ---


def test_disable_deletes_secret() -> None:
    """--disable deletes the GitHub Actions secret."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key", "--disable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted ANTHROPIC_API_KEY" in result.output
        assert len(admin.delete_secret_calls) == 1
        assert admin.delete_secret_calls[0] == "ANTHROPIC_API_KEY"

"""Unit tests for admin gh-actions-api-key command."""

import os
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.fakes.gateway.github_admin import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env

# --- Status display tests ---


def test_status_enabled() -> None:
    """Display mode shows ANTHROPIC_API_KEY as Set and Active."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "ANTHROPIC_API_KEY" in result.output
        assert "Active: ANTHROPIC_API_KEY" in result.output


def test_status_not_found() -> None:
    """Display mode shows Not set and guidance when no secrets exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Not set" in result.output
        assert "No authentication configured" in result.output


def test_status_api_error() -> None:
    """Display mode shows Error when secret_exists returns None."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secret_check_error=True)
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Error" in result.output


def test_status_shows_both_set_with_precedence() -> None:
    """When both secrets are set, ANTHROPIC_API_KEY takes precedence."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "ANTHROPIC_API_KEY" in result.output
        assert "CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert "takes precedence" in result.output


def test_status_shows_oauth_only() -> None:
    """When only oauth secret is set, it shows as active."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Active: CLAUDE_CODE_OAUTH_TOKEN" in result.output


def test_status_shows_local_env_vars() -> None:
    """Status display shows local env var status."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"GH_ACTIONS_ANTHROPIC_API_KEY": "sk-test"}):
            result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "GH_ACTIONS_ANTHROPIC_API_KEY: Set" in result.output


# --- Enable tests ---


def test_enable_sets_secret() -> None:
    """--enable reads GH_ACTIONS_ANTHROPIC_API_KEY env var and sets GitHub Actions secret."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"GH_ACTIONS_ANTHROPIC_API_KEY": "sk-test-123"}):
            result = runner.invoke(cli, ["admin", "gh-actions-api-key", "--enable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set ANTHROPIC_API_KEY" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "ANTHROPIC_API_KEY"
        assert value == "sk-test-123"
        # Verify other secret was deleted to prevent ambiguity
        assert len(admin.delete_secret_calls) == 1
        assert admin.delete_secret_calls[0] == "CLAUDE_CODE_OAUTH_TOKEN"


def test_enable_prompts_when_env_var_not_set() -> None:
    """--enable prompts interactively when GH_ACTIONS_ANTHROPIC_API_KEY is not set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        env_copy = {k: v for k, v in os.environ.items() if k != "GH_ACTIONS_ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env_copy, clear=True):
            result = runner.invoke(
                cli,
                ["admin", "gh-actions-api-key", "--enable"],
                obj=ctx,
                input="sk-prompted-key\n",
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set ANTHROPIC_API_KEY" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "ANTHROPIC_API_KEY"
        assert value == "sk-prompted-key"


def test_enable_oauth_sets_oauth_secret() -> None:
    """--oauth --enable sets CLAUDE_CODE_OAUTH_TOKEN and deletes ANTHROPIC_API_KEY."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN": "oauth-token-123"}):
            result = runner.invoke(
                cli, ["admin", "gh-actions-api-key", "--oauth", "--enable"], obj=ctx
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "CLAUDE_CODE_OAUTH_TOKEN"
        assert value == "oauth-token-123"
        # Verify ANTHROPIC_API_KEY was deleted to prevent ambiguity
        assert len(admin.delete_secret_calls) == 1
        assert admin.delete_secret_calls[0] == "ANTHROPIC_API_KEY"


def test_enable_oauth_prompts_when_env_var_not_set() -> None:
    """--oauth --enable prompts when GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN is not set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        env_copy = {
            k: v for k, v in os.environ.items() if k != "GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN"
        }
        with patch.dict("os.environ", env_copy, clear=True):
            result = runner.invoke(
                cli,
                ["admin", "gh-actions-api-key", "--oauth", "--enable"],
                obj=ctx,
                input="oauth-prompted-token\n",
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "CLAUDE_CODE_OAUTH_TOKEN"
        assert value == "oauth-prompted-token"


# --- Disable tests ---


def test_disable_deletes_secret() -> None:
    """--disable deletes the ANTHROPIC_API_KEY secret."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key", "--disable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted ANTHROPIC_API_KEY" in result.output
        assert len(admin.delete_secret_calls) == 1
        assert admin.delete_secret_calls[0] == "ANTHROPIC_API_KEY"


def test_disable_oauth_deletes_oauth_secret() -> None:
    """--oauth --disable deletes only CLAUDE_CODE_OAUTH_TOKEN."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(
            cli, ["admin", "gh-actions-api-key", "--oauth", "--disable"], obj=ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert len(admin.delete_secret_calls) == 1
        assert admin.delete_secret_calls[0] == "CLAUDE_CODE_OAUTH_TOKEN"

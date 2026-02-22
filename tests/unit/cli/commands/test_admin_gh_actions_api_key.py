"""Unit tests for admin gh-actions-api-key command."""

import os
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env

# --- Status display tests ---


def test_status_shows_both_secrets() -> None:
    """Status shows both secrets with active label on API key when both are set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "ANTHROPIC_API_KEY:" in result.output
        assert "CLAUDE_CODE_OAUTH_TOKEN:" in result.output
        assert "active (takes precedence)" in result.output


def test_status_only_api_key() -> None:
    """Status shows API key as active when only API key is set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Active: ANTHROPIC_API_KEY" in result.output


def test_status_only_oauth() -> None:
    """Status shows OAuth token as active when only OAuth is set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Active: CLAUDE_CODE_OAUTH_TOKEN" in result.output


def test_status_neither_configured() -> None:
    """Status shows guidance message when neither secret is configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "No authentication secret configured." in result.output
        assert "--enable" in result.output
        assert "--oauth" in result.output


def test_status_api_error() -> None:
    """Status shows Error when secret_exists returns None."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secret_check_error=True)
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "gh-actions-api-key"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Error" in result.output


# --- Enable API key tests ---


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


def test_enable_api_key_deletes_oauth() -> None:
    """--enable (no --oauth) deletes CLAUDE_CODE_OAUTH_TOKEN when switching."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"GH_ACTIONS_ANTHROPIC_API_KEY": "sk-test-123"}):
            result = runner.invoke(cli, ["admin", "gh-actions-api-key", "--enable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set ANTHROPIC_API_KEY" in result.output
        assert "CLAUDE_CODE_OAUTH_TOKEN" in admin.delete_secret_calls


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


# --- Disable API key tests ---


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


# --- Enable OAuth tests ---


def test_enable_oauth_sets_oauth_secret() -> None:
    """--enable --oauth sets CLAUDE_CODE_OAUTH_TOKEN from env var."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets=set())
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN": "oauth-token-123"}):
            result = runner.invoke(
                cli, ["admin", "gh-actions-api-key", "--enable", "--oauth"], obj=ctx
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "CLAUDE_CODE_OAUTH_TOKEN"
        assert value == "oauth-token-123"


def test_enable_oauth_deletes_api_key() -> None:
    """--enable --oauth deletes ANTHROPIC_API_KEY when switching."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(github_admin=admin)

        with patch.dict("os.environ", {"GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN": "oauth-token-123"}):
            result = runner.invoke(
                cli, ["admin", "gh-actions-api-key", "--enable", "--oauth"], obj=ctx
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert "ANTHROPIC_API_KEY" in admin.delete_secret_calls


def test_enable_oauth_prompts_when_env_var_not_set() -> None:
    """--enable --oauth prompts when GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN is not set."""
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
                ["admin", "gh-actions-api-key", "--enable", "--oauth"],
                obj=ctx,
                input="oauth-prompted-token\n",
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Set CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert len(admin.set_secret_calls) == 1
        name, value = admin.set_secret_calls[0]
        assert name == "CLAUDE_CODE_OAUTH_TOKEN"
        assert value == "oauth-prompted-token"


# --- Disable OAuth tests ---


def test_disable_oauth_deletes_oauth_secret() -> None:
    """--disable --oauth deletes the CLAUDE_CODE_OAUTH_TOKEN secret."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(secrets={"CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(
            cli, ["admin", "gh-actions-api-key", "--disable", "--oauth"], obj=ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted CLAUDE_CODE_OAUTH_TOKEN" in result.output
        assert len(admin.delete_secret_calls) == 1
        assert admin.delete_secret_calls[0] == "CLAUDE_CODE_OAUTH_TOKEN"

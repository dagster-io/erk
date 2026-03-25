"""Unit tests for admin claude-ci command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.fakes.gateway.github_admin import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env

# --- Status display tests ---


def test_status_enabled() -> None:
    """Display mode shows Enabled when CLAUDE_ENABLED variable is 'true'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(variables={"CLAUDE_ENABLED": "true"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "claude-ci"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Enabled" in result.output


def test_status_disabled() -> None:
    """Display mode shows Disabled when CLAUDE_ENABLED variable is 'false'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(variables={"CLAUDE_ENABLED": "false"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "claude-ci"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Disabled" in result.output


def test_status_not_set() -> None:
    """Display mode shows Enabled (default) when CLAUDE_ENABLED variable is not set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "claude-ci"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Enabled" in result.output


# --- Enable tests ---


def test_enable_sets_variable() -> None:
    """--enable calls set_variable with 'true'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "claude-ci", "--enable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Enabled" in result.output
        assert len(admin.set_variable_calls) == 1
        name, value = admin.set_variable_calls[0]
        assert name == "CLAUDE_ENABLED"
        assert value == "true"


# --- Disable tests ---


def test_disable_sets_variable() -> None:
    """--disable calls set_variable with 'false'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        admin = FakeGitHubAdmin(variables={"CLAUDE_ENABLED": "true"})
        ctx = env.build_context(github_admin=admin)

        result = runner.invoke(cli, ["admin", "claude-ci", "--disable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Disabled" in result.output
        assert len(admin.set_variable_calls) == 1
        name, value = admin.set_variable_calls[0]
        assert name == "CLAUDE_ENABLED"
        assert value == "false"

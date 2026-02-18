"""Unit tests for admin auth-source command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_display_shows_current_value() -> None:
    """Display mode shows the current auth source variable value."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin(
            variables={"CLAUDE_AUTH_SOURCE": "ANTHROPIC_API_KEY"},
        )
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "auth-source"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "ANTHROPIC_API_KEY" in result.output


def test_display_shows_not_set() -> None:
    """Display mode shows 'Not set' when variable is not configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "auth-source"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Not set" in result.output


def test_set_anthropic_api_key() -> None:
    """--set ANTHROPIC_API_KEY calls set_variable correctly."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "auth-source", "--set", "ANTHROPIC_API_KEY"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(fake_admin.set_variable_calls) == 1
        name, value = fake_admin.set_variable_calls[0]
        assert name == "CLAUDE_AUTH_SOURCE"
        assert value == "ANTHROPIC_API_KEY"


def test_set_oauth_token() -> None:
    """--set CLAUDE_CODE_OAUTH_TOKEN calls set_variable correctly."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(
            cli, ["admin", "auth-source", "--set", "CLAUDE_CODE_OAUTH_TOKEN"], obj=ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(fake_admin.set_variable_calls) == 1
        name, value = fake_admin.set_variable_calls[0]
        assert name == "CLAUDE_AUTH_SOURCE"
        assert value == "CLAUDE_CODE_OAUTH_TOKEN"


def test_error_no_github_remote() -> None:
    """Command fails with clear error when repo has no GitHub remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={env.cwd, env.git_dir},
            remote_urls={},
        )
        ctx = env.build_context(git=git)

        result = runner.invoke(cli, ["admin", "auth-source"], obj=ctx)

        assert result.exit_code == 1
        assert "Not a GitHub repository" in result.output

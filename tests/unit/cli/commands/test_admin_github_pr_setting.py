"""Unit tests for admin github-pr-setting command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_display_mode_shows_enabled() -> None:
    """Display mode shows Enabled when permission is granted."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin(
            workflow_permissions={"can_approve_pull_request_reviews": True},
        )
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "github-pr-setting"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Enabled" in result.output


def test_display_mode_shows_disabled() -> None:
    """Display mode shows Disabled when permission is not granted."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "github-pr-setting"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Disabled" in result.output


def test_enable_mode_sets_permission() -> None:
    """--enable flag calls set_workflow_pr_permissions with enabled=True."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "github-pr-setting", "--enable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(fake_admin.set_permission_calls) == 1
        repo_root, enabled = fake_admin.set_permission_calls[0]
        assert repo_root == env.root_worktree
        assert enabled is True


def test_disable_mode_sets_permission() -> None:
    """--disable flag calls set_workflow_pr_permissions with enabled=False."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        fake_admin = FakeGitHubAdmin()
        ctx = env.build_context(github_admin=fake_admin)

        result = runner.invoke(cli, ["admin", "github-pr-setting", "--disable"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(fake_admin.set_permission_calls) == 1
        repo_root, enabled = fake_admin.set_permission_calls[0]
        assert repo_root == env.root_worktree
        assert enabled is False


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

        result = runner.invoke(cli, ["admin", "github-pr-setting"], obj=ctx)

        assert result.exit_code == 1
        assert "Not a GitHub repository" in result.output

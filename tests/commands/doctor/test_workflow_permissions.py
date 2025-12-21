"""Tests for workflow permissions health check."""

from click.testing import CliRunner

from erk.core.health_checks import check_workflow_permissions
from erk_shared.git.fake import FakeGit
from tests.fakes.github_admin import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_check_workflow_permissions_no_origin_remote() -> None:
    """Test check_workflow_permissions when no origin remote is configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit with no remote_urls configured - get_remote_url will raise ValueError
        # Use env.build_context() directly to avoid build_workspace_test_context
        # auto-adding a default remote URL
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # No remote_urls - get_remote_url will raise ValueError
        )

        ctx = env.build_context(git=git)
        admin = FakeGitHubAdmin()

        result = check_workflow_permissions(ctx, env.cwd, admin)

        # Should pass (info level) with appropriate message
        assert result.passed is True
        assert result.name == "workflow permissions"
        assert "No origin remote configured" in result.message


def test_check_workflow_permissions_non_github_remote() -> None:
    """Test check_workflow_permissions when remote is not GitHub."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit with a non-GitHub remote URL
        # Use env.build_context() directly to avoid build_workspace_test_context
        # overwriting the remote URL
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://gitlab.com/owner/repo.git"},
        )

        ctx = env.build_context(git=git)
        admin = FakeGitHubAdmin()

        result = check_workflow_permissions(ctx, env.cwd, admin)

        # Should pass (info level) with appropriate message
        assert result.passed is True
        assert result.name == "workflow permissions"
        assert "Not a GitHub repository" in result.message

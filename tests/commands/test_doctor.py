"""Tests for erk doctor command."""

from click.testing import CliRunner

from erk.cli.commands.doctor import doctor_cmd
from erk.core.health_checks import check_workflow_permissions
from erk_shared.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_doctor_runs_checks() -> None:
    """Test that doctor command runs and displays check results."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        # Command should succeed
        assert result.exit_code == 0

        # Should show section headers
        assert "Checking erk setup" in result.output
        assert "CLI Tools" in result.output
        assert "Repository Setup" in result.output

        # Should show erk version check
        assert "erk" in result.output.lower()


def test_doctor_shows_cli_availability() -> None:
    """Test that doctor shows CLI tool availability."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0

        # Should check for common tools (they may or may not be installed)
        # The output should mention each tool name
        output_lower = result.output.lower()
        assert "claude" in output_lower or "claude" in result.output
        assert "graphite" in output_lower or "gt" in output_lower
        assert "github" in output_lower or "gh" in output_lower


def test_doctor_shows_repository_status() -> None:
    """Test that doctor shows repository setup status."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show repository check
        assert "Repository Setup" in result.output


def test_doctor_shows_summary() -> None:
    """Test that doctor shows a summary at the end."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show either "All checks passed" or "check(s) failed"
        assert "passed" in result.output.lower() or "failed" in result.output.lower()


def test_doctor_shows_github_section() -> None:
    """Test that doctor shows GitHub section with auth and workflow permissions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show GitHub section header
        assert "GitHub" in result.output


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

        result = check_workflow_permissions(ctx, env.cwd)

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

        result = check_workflow_permissions(ctx, env.cwd)

        # Should pass (info level) with appropriate message
        assert result.passed is True
        assert result.name == "workflow permissions"
        assert "Not a GitHub repository" in result.message

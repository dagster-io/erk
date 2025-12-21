"""Tests for erk doctor command - production command integration tests."""

from click.testing import CliRunner

from erk.cli.commands.doctor import doctor_cmd
from erk.core.implementation_queue.github.abc import AuthStatus
from erk_shared.git.fake import FakeGit
from tests.fakes.github_admin import FakeGitHubAdmin
from tests.fakes.shell import FakeShell
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_test_shell() -> FakeShell:
    """Create a FakeShell configured with all tools installed for tests."""
    return FakeShell(
        installed_tools={
            "claude": "/usr/local/bin/claude",
            "gt": "/usr/local/bin/gt",
            "gh": "/usr/local/bin/gh",
            "uv": "/usr/local/bin/uv",
        },
        tool_versions={
            "claude": "claude 1.0.41",
            "gt": "0.29.17",
            "gh": "gh version 2.66.1 (2025-01-15)\nhttps://github.com/cli/cli/releases/tag/v2.66.1",
            "uv": "uv 0.5.20",
        },
    )


def _make_test_admin() -> FakeGitHubAdmin:
    """Create a FakeGitHubAdmin configured for tests."""
    return FakeGitHubAdmin(
        auth_status=AuthStatus(authenticated=True, username="testuser", error=None),
        workflow_permissions={
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        },
    )


def test_doctor_runs_checks() -> None:
    """Test that doctor command runs and displays check results."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

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

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0

        # Should check for common tools - now all should show as available with versions
        output_lower = result.output.lower()
        assert "claude" in output_lower
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

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

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

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

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

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show GitHub section header
        assert "GitHub" in result.output

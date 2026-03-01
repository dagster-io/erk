"""Tests for erk doctor workflow CLI subcommand."""

from click.testing import CliRunner

from erk.cli.commands.doctor import doctor_cmd
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github_admin.abc import AuthStatus
from tests.fakes.github_admin import FakeGitHubAdmin
from tests.fakes.shell import FakeShell
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_test_shell() -> FakeShell:
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
    return FakeGitHubAdmin(
        auth_status=AuthStatus(authenticated=True, username="testuser", error=None),
        workflow_permissions={
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        },
    )


def test_doctor_workflow_check_runs_static_checks() -> None:
    """Test that 'erk doctor workflow check' runs workflow-focused checks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            shell=_make_test_shell(),
            github_admin=_make_test_admin(),
        )

        result = runner.invoke(doctor_cmd, ["workflow", "check"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow Checks" in result.output


def test_doctor_workflow_bare_shows_help() -> None:
    """Test that 'erk doctor workflow' (no subcommand) shows help."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            shell=_make_test_shell(),
            github_admin=_make_test_admin(),
        )

        result = runner.invoke(doctor_cmd, ["workflow"], obj=ctx)

        assert result.exit_code == 0
        assert "check" in result.output
        assert "smoke-test" in result.output
        assert "cleanup" in result.output


def test_doctor_workflow_cleanup_with_no_artifacts() -> None:
    """Test that 'erk doctor workflow cleanup' with no smoke artifacts shows appropriate message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
            remote_branches={env.cwd: ["origin/main"]},
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            shell=_make_test_shell(),
            github_admin=_make_test_admin(),
        )

        result = runner.invoke(doctor_cmd, ["workflow", "cleanup"], obj=ctx)

        assert result.exit_code == 0
        assert "No smoke test artifacts found" in result.output


def test_doctor_still_works_without_subcommand() -> None:
    """Test that 'erk doctor' (no subcommand) still works as before."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        assert "Checking erk setup" in result.output
        assert "Repository Setup" in result.output
        assert "User Setup" in result.output

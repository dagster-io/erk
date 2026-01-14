"""Tests for erk doctor command - production command integration tests."""

import pytest
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
        assert "Repository Setup" in result.output
        assert "User Setup" in result.output

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


def test_doctor_shows_github_checks() -> None:
    """Test that doctor shows GitHub-related checks in appropriate sections."""
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
        # GitHub auth check should be under User Setup
        # workflow-permissions should be under Repository Setup > GitHub subgroup
        assert "GitHub" in result.output  # GitHub subgroup in repo section


def test_doctor_shows_required_version_check() -> None:
    """Test that doctor shows required version check result."""
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
        # Should include version-related check in output
        # The check will fail because no version file exists, but it should appear
        output_lower = result.output.lower()
        assert "version" in output_lower


def test_doctor_shows_exit_plan_hook_check() -> None:
    """Test that doctor shows exit plan hook check result."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        # Create .claude/settings.json so we can check for the specific exit-plan-hook message
        settings_path = env.cwd / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text('{"hooks": {}}', encoding="utf-8")

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should include exit plan hook check in output (message contains "ExitPlanMode")
        # When settings.json exists but hook is not configured, message is
        # "ExitPlanMode hook not configured"
        assert "ExitPlanMode" in result.output


def test_doctor_default_shows_condensed_subgroups() -> None:
    """Test that doctor default output shows condensed sub-group summaries."""
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
        # Should show sub-group names with "(X checks)" format
        # At least one sub-group should be shown with check count
        assert "checks)" in result.output


def test_doctor_verbose_shows_all_individual_checks() -> None:
    """Test that --verbose flag shows all individual checks expanded."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, ["--verbose"], obj=ctx)

        assert result.exit_code == 0
        # In verbose mode, should show sub-group headers like "Git repository"
        assert "Git repository" in result.output
        # Should show individual checks expanded (more detail visible)
        # The sub-group header style is dim text
        assert "Claude settings" in result.output or "Erk configuration" in result.output


def test_doctor_verbose_short_flag() -> None:
    """Test that -v short flag works for verbose mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, ["-v"], obj=ctx)

        assert result.exit_code == 0
        # Same as --verbose, should show sub-group headers
        assert "Git repository" in result.output


def test_doctor_dogfooder_hides_checks_by_default() -> None:
    """Test that early dogfooder checks are not shown by default."""
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
        # Early Dogfooder section should NOT appear by default
        assert "Early Dogfooder" not in result.output


def test_doctor_dogfooder_flag_shows_checks() -> None:
    """Test that --dogfooder flag shows early dogfooder checks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, ["--dogfooder"], obj=ctx)

        assert result.exit_code == 0
        # Early Dogfooder section SHOULD appear when flag is passed
        assert "Early Dogfooder" in result.output


def test_doctor_subgroup_auto_expands_on_failure() -> None:
    """Test that sub-groups with failures auto-expand to show failed checks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        # Create .claude/settings.json but without the required hooks
        # This will cause user-prompt-hook and exit-plan-hook to fail
        settings_path = env.cwd / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text('{"hooks": {}}', encoding="utf-8")

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        # Command should succeed but with failures
        assert result.exit_code == 0

        # Should show the failing checks expanded (not just count)
        # When hooks are missing, should show specific failure messages
        assert "hook" in result.output.lower()


def test_doctor_clear_hook_logs_clears_logs_and_shows_count() -> None:
    """Test that --clear-hook-logs clears logs and shows the count."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        # Create some hook log files
        session_dir = env.cwd / ".erk" / "scratch" / "sessions" / "test-session"
        hook_dir = session_dir / "hooks" / "my-hook"
        hook_dir.mkdir(parents=True)
        (hook_dir / "log1.json").write_text("{}", encoding="utf-8")
        (hook_dir / "log2.json").write_text("{}", encoding="utf-8")

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, ["--clear-hook-logs"], obj=ctx)

        # Should succeed
        assert result.exit_code == 0
        # Should show count of cleared logs
        assert "Cleared 2 hook log(s)" in result.output
        # Should NOT run normal diagnostics
        assert "Checking erk setup" not in result.output
        # Files should be deleted
        assert not (hook_dir / "log1.json").exists()
        assert not (hook_dir / "log2.json").exists()


def test_doctor_clear_hook_logs_with_no_logs() -> None:
    """Test that --clear-hook-logs with no logs shows '0 logs'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        # No hook logs exist
        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        result = runner.invoke(doctor_cmd, ["--clear-hook-logs"], obj=ctx)

        # Should succeed
        assert result.exit_code == 0
        # Should show zero count
        assert "Cleared 0 hook log(s)" in result.output


def test_doctor_shows_remediation_for_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that doctor shows remediation for warning checks (not just failures).

    This test verifies that when a CheckResult has warning=True with a remediation,
    the doctor command displays the remediation message. This was a bug where
    remediations were only shown for failed checks (passed=False), not warnings.
    """
    from erk.core.health_checks import CheckResult

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        # Create minimal settings.json so Claude settings check passes
        settings_path = env.cwd / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text('{"permissions": {"allow": ["Bash(erk:*)"]}}', encoding="utf-8")

        ctx = build_workspace_test_context(env, git=git, shell=_make_test_shell())

        # Mock run_all_checks to return a warning with remediation
        def mock_run_all_checks(_ctx):  # type: ignore[no-untyped-def]
            return [
                # A passing check (no warning)
                CheckResult(
                    name="test-pass",
                    passed=True,
                    message="Test passed",
                ),
                # A warning check with remediation - this is what we're testing
                CheckResult(
                    name="test-warning",
                    passed=True,  # Still passes but has warning
                    warning=True,
                    message="Test has warning",
                    remediation="Run 'test-command' to fix the warning",
                ),
            ]

        from erk.cli.commands import doctor as doctor_module

        monkeypatch.setattr(
            doctor_module,
            "run_all_checks",
            mock_run_all_checks,
        )

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        # Command should succeed (no failures)
        assert result.exit_code == 0

        # CRITICAL: Should show remediation section for the warning
        assert "Remediation" in result.output
        assert "test-command" in result.output

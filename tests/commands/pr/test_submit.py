"""Tests for erk pr submit command."""

from click.testing import CliRunner
from erk_shared.git.branches.fake import FakeGitBranches
from erk_shared.git.fake import FakeGit

from erk.cli.commands.pr import pr_group
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_submit_success() -> None:
    """Test successful PR submission."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_pr_url="https://github.com/owner/repo/pull/123",
            simulated_pr_number=123,
            simulated_pr_title="Test PR",
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        assert "https://github.com/owner/repo/pull/123" in result.output

        # Verify the slash command was called
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous, _ = claude_executor.executed_commands[0]
        assert command == "/gt:pr-submit"
        assert dangerous is False


def test_pr_submit_success_without_pr_url() -> None:
    """Test successful PR submission without PR URL in result."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        # Success without PR URL (edge case)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_pr_url=None,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        # Should still succeed
        assert result.exit_code == 0
        # No PR URL line
        assert "🔗 PR:" not in result.output


def test_pr_submit_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            local_branches={env.cwd: ["main"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(claude_executor.executed_commands) == 0


def test_pr_submit_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakeClaudeExecutor
        assert "failed" in result.output.lower()


def test_pr_submit_shows_error_on_no_output() -> None:
    """Test that command fails when Claude produces no output."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_no_output=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "no output" in result.output.lower()


def test_pr_submit_shows_error_on_process_error() -> None:
    """Test that command fails when Claude fails to start."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_process_error="Failed to start: Permission denied",
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Permission denied" in result.output


def test_pr_submit_shows_error_on_zero_turns() -> None:
    """Test that command fails when Claude completes with zero turns (hook blocking)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_branches = FakeGitBranches(
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            git_branches=git_branches,
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_zero_turns=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "completed without processing" in result.output
        assert "hook blocked" in result.output
        # Should include helpful suggestion
        assert "Run 'claude" in result.output or "claude /gt:pr-submit" in result.output

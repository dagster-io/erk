"""Tests for erk pr address command (local variant)."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_address_success() -> None:
    """Test successful local address when Claude is available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["address", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "PR comments addressed!" in result.output

        # Claude should be invoked for PR comment addressing
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous_flag, _, _ = claude_executor.executed_commands[0]
        assert command == "/erk:pr-address"
        assert dangerous_flag is True


def test_pr_address_requires_dangerous_flag() -> None:
    """Test that command fails when --dangerous flag is not provided."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["address"], obj=ctx)

        assert result.exit_code != 0
        assert "Missing option '--dangerous'" in result.output


def test_pr_address_claude_not_available() -> None:
    """Test error when Claude is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["address", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(claude_executor.executed_commands) == 0


def test_pr_address_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["address", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakeClaudeExecutor
        assert "failed" in result.output.lower()

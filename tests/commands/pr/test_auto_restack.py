"""Tests for erk pr auto-restack command."""

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit

from erk.cli.commands.pr import pr_group
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_auto_restack_success() -> None:
    """Test successful auto-restack."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Verify the slash command was called
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous, _ = claude_executor.executed_commands[0]
        assert command == "/erk:auto-restack"
        assert dangerous is True  # Restack modifies git state


def test_pr_auto_restack_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(claude_executor.executed_commands) == 0


def test_pr_auto_restack_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakeClaudeExecutor
        assert "failed" in result.output.lower()


def test_pr_auto_restack_aborts_on_semantic_conflict() -> None:
    """Test that command aborts when Claude prompts for user input (semantic conflict)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        # Simulate Claude using AskUserQuestion tool (semantic conflict)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_tool_events=["Using AskUserQuestion..."],
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        # Should fail with semantic conflict message
        assert result.exit_code != 0
        assert "Semantic conflict detected" in result.output
        assert "interactive resolution" in result.output
        assert "claude /erk:auto-restack" in result.output

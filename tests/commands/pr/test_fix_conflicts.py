"""Tests for erk pr fix-conflicts command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.context.types import GlobalConfig
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_fix_conflicts_success() -> None:
    """Test successful fix-conflicts when conflicts exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],  # Has conflicts
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "Conflicts resolved!" in result.output

        # Claude should be invoked for conflict resolution
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous_flag, _, _ = claude_executor.executed_commands[0]
        assert command == "/erk:fix-conflicts"
        assert dangerous_flag is True


def test_pr_fix_conflicts_requires_dangerous_flag() -> None:
    """Test that command fails when --dangerous flag is not provided (default config)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts"], obj=ctx)

        assert result.exit_code != 0
        assert "Missing option '--dangerous'" in result.output
        # Verify error message includes config hint
        assert "fix_conflicts_require_dangerous_flag false" in result.output


def test_pr_fix_conflicts_skip_dangerous_with_config() -> None:
    """Test that --dangerous flag is not required when config disables requirement."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],  # Has conflicts
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Create GlobalConfig with fix_conflicts_require_dangerous_flag=False
        global_config = GlobalConfig.test(
            env.erk_root,
            fix_conflicts_require_dangerous_flag=False,  # Disable --dangerous requirement
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            claude_executor=claude_executor,
            global_config=global_config,
        )

        # Invoke WITHOUT --dangerous flag
        result = runner.invoke(pr_group, ["fix-conflicts"], obj=ctx)

        # Should succeed without --dangerous when config disables requirement
        assert result.exit_code == 0
        assert "Conflicts resolved!" in result.output


def test_pr_fix_conflicts_no_conflicts() -> None:
    """Test early exit when no conflicts detected."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=[],  # No conflicts
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "No merge conflicts detected" in result.output

        # Claude should NOT be invoked (no conflicts to resolve)
        assert len(claude_executor.executed_commands) == 0


def test_pr_fix_conflicts_claude_not_available() -> None:
    """Test error when Claude is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],  # Has conflicts
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(claude_executor.executed_commands) == 0


def test_pr_fix_conflicts_aborts_on_semantic_conflict() -> None:
    """Test that command aborts when Claude prompts for user input (semantic conflict)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],  # Has conflicts
        )

        # Simulate Claude using AskUserQuestion tool (semantic conflict)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_tool_events=["Using AskUserQuestion..."],
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts", "--dangerous"], obj=ctx)

        # Should fail with semantic conflict message
        assert result.exit_code != 0
        assert "Semantic conflict detected" in result.output
        assert "interactive resolution" in result.output
        assert "claude /erk:fix-conflicts" in result.output


def test_pr_fix_conflicts_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],  # Has conflicts
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakeClaudeExecutor
        assert "failed" in result.output.lower()


def test_pr_fix_conflicts_fails_when_no_work_events() -> None:
    """Test that command fails when Claude completes but produces no work events."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            conflicted_files=["src/file.py"],  # Has conflicts
        )

        # Simulate Claude completing but emitting no work events
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_no_work_events=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["fix-conflicts", "--dangerous"], obj=ctx)

        # Should fail due to no work events
        assert result.exit_code != 0
        assert "without producing any output" in result.output
        assert "check hooks" in result.output

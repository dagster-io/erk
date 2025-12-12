"""Tests for erk pr auto-restack command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_auto_restack_success() -> None:
    """Test successful auto-restack via fast path (no conflicts)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=False,  # No conflicts
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Fast path: Claude should NOT be invoked (no conflicts)
        assert len(claude_executor.executed_commands) == 0

        # Graphite restack should have been called
        assert len(graphite.restack_calls) == 1


def test_pr_auto_restack_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available and conflicts exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code != 0
        assert "Conflicts require Claude" in result.output
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
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

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
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        # Simulate Claude using AskUserQuestion tool (semantic conflict)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_tool_events=["Using AskUserQuestion..."],
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        # Should fail with semantic conflict message
        assert result.exit_code != 0
        assert "Semantic conflict detected" in result.output
        assert "interactive resolution" in result.output
        assert "claude /erk:auto-restack" in result.output


def test_pr_auto_restack_fallback_on_conflicts() -> None:
    """Test fallback: conflicts detected, Claude IS invoked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Single commit, no squash needed
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        # Claude handles it, so should succeed
        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Fallback path: Claude SHOULD be invoked
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous, _ = claude_executor.executed_commands[0]
        assert command == "/erk:auto-restack"
        assert dangerous is True


def test_pr_auto_restack_fast_path_with_rebase_in_progress_but_no_conflicts() -> None:
    """Test fast path: rebase in progress but no actual conflicts (rebase_continue clears state)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Rebase in progress...
            conflicted_files=[],  # ...but NO actual conflicts
            rebase_continue_clears_rebase=True,  # rebase_continue will complete the rebase
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Fast path: Claude should NOT be invoked (no actual conflicts)
        assert len(claude_executor.executed_commands) == 0

        # rebase_continue should have been called to clear the rebase state
        assert len(git.rebase_continue_calls) == 1


def test_pr_auto_restack_preflight_error() -> None:
    """Test preflight error: error reported, Claude NOT invoked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 0},  # No commits - this should error
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        # Preflight error
        assert result.exit_code != 0
        assert "No commits found" in result.output

        # Preflight error: Claude should NOT be invoked
        assert len(claude_executor.executed_commands) == 0


def test_pr_auto_restack_auto_commits_dirty_working_tree() -> None:
    """Test that command auto-commits when working tree has uncommitted changes."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            dirty_worktrees={env.cwd},  # Working tree has uncommitted changes
            rebase_in_progress=False,  # No conflicts
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        # Should succeed after auto-committing
        assert result.exit_code == 0
        assert "Auto-committing" in result.output

        # A commit should have been created with the WIP message
        assert len(git.commits) >= 1
        commit_messages = [msg for _, msg, _ in git.commits]
        assert "WIP: auto-commit before restack" in commit_messages

        # Graphite restack should have been called (we proceed after auto-commit)
        assert len(graphite.restack_calls) == 1

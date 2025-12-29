"""Tests for erk pr fix-conflicts command.

The fix-conflicts command helps resolve merge conflicts during rebase
by invoking Claude for assistance.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr.fix_conflicts_cmd import pr_fix_conflicts
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_fix_conflicts_no_rebase_no_conflicts_errors() -> None:
    """Test that fix-conflicts errors when there's no rebase and no conflicts."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ],
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            repository_roots={env.root_worktree: env.root_worktree},
            rebase_in_progress=False,
            conflicted_files=[],
        )

        test_ctx = env.build_context(git=git)

        result = runner.invoke(pr_fix_conflicts, [], obj=test_ctx)

        assert result.exit_code == 1
        assert "No rebase in progress" in result.output
        assert "no conflicts detected" in result.output.lower()


def test_fix_conflicts_no_conflicts_during_rebase() -> None:
    """Test that fix-conflicts reports success when rebase is in progress but no conflicts."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ],
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            repository_roots={env.root_worktree: env.root_worktree},
            rebase_in_progress=True,
            conflicted_files=[],  # No conflicts
        )

        test_ctx = env.build_context(git=git)

        result = runner.invoke(pr_fix_conflicts, [], obj=test_ctx)

        assert result.exit_code == 0
        assert "No conflicts detected" in result.output


def test_fix_conflicts_invokes_claude() -> None:
    """Test that fix-conflicts invokes Claude when conflicts exist."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ],
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            repository_roots={env.root_worktree: env.root_worktree},
            rebase_in_progress=True,
            conflicted_files=["src/main.py", "tests/test_main.py"],
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Simulate Claude fixing conflicts
        original_execute = claude_executor.execute_command_streaming

        def execute_and_fix_conflicts(
            command: str,
            worktree_path: Path,
            dangerous: bool,
            verbose: bool = False,
            debug: bool = False,
        ):
            for event in original_execute(command, worktree_path, dangerous, verbose, debug):
                yield event
            # Simulate Claude fixing conflicts
            git._conflicted_files = []
            git._rebase_in_progress = False

        claude_executor.execute_command_streaming = execute_and_fix_conflicts

        test_ctx = env.build_context(git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_fix_conflicts, [], obj=test_ctx)

        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"

        # Should have mentioned the conflicted files
        assert "src/main.py" in result.output or "2 conflict" in result.output

        # Claude should have been invoked
        assert len(claude_executor.executed_commands) >= 1


def test_fix_conflicts_without_claude_available() -> None:
    """Test that fix-conflicts fails gracefully when Claude is not available."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ],
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            repository_roots={env.root_worktree: env.root_worktree},
            rebase_in_progress=True,
            conflicted_files=["src/main.py"],
        )

        # Claude NOT available
        claude_executor = FakeClaudeExecutor(claude_available=False)

        test_ctx = env.build_context(git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_fix_conflicts, [], obj=test_ctx)

        assert result.exit_code == 1
        assert "Claude" in result.output
        assert "claude.com/download" in result.output


def test_fix_conflicts_with_conflicts_but_no_rebase() -> None:
    """Test that fix-conflicts still works when conflicts exist without rebase in progress.

    This handles edge cases where git state is partially cleaned up but
    conflicted files remain.
    """
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ],
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            repository_roots={env.root_worktree: env.root_worktree},
            rebase_in_progress=False,  # No rebase
            conflicted_files=["src/main.py"],  # But conflicts exist
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Simulate Claude fixing conflicts
        original_execute = claude_executor.execute_command_streaming

        def execute_and_fix_conflicts(
            command: str,
            worktree_path: Path,
            dangerous: bool,
            verbose: bool = False,
            debug: bool = False,
        ):
            for event in original_execute(command, worktree_path, dangerous, verbose, debug):
                yield event
            git._conflicted_files = []

        claude_executor.execute_command_streaming = execute_and_fix_conflicts

        test_ctx = env.build_context(git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_fix_conflicts, [], obj=test_ctx)

        # Should succeed - we handle this edge case
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"

        # Should warn about unusual state
        assert "no rebase in progress" in result.output.lower()


def test_fix_conflicts_semantic_conflict_requires_interactive() -> None:
    """Test that fix-conflicts reports when semantic conflicts need human intervention.

    When Claude's auto-restack returns requires_interactive=True, the command
    should fail with a clear error directing the user to manual resolution.
    """
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ],
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            repository_roots={env.root_worktree: env.root_worktree},
            rebase_in_progress=True,
            conflicted_files=["src/main.py"],
        )

        # Claude executor that simulates a semantic conflict (requires interactive)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,  # Simulates failure
        )

        test_ctx = env.build_context(git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_fix_conflicts, [], obj=test_ctx)

        # Should fail since Claude couldn't resolve automatically
        assert result.exit_code == 1

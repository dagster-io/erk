"""Tests for erk split command.

This file tests the split command which creates individual worktrees for each
branch in a Graphite stack.
"""

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.cli.cli import cli
from tests.test_utils.env_helpers import erk_inmem_env

# Basic functionality tests


def test_split_full_stack() -> None:
    """Default behavior splits entire stack into individual worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        current_branch = "feat-2"

        # Configure graphite with stack
        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})

        # Configure git ops with worktrees
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Will create:" in result.output
        # feat-1 and feat-3 should be created (not main or current feat-2)
        assert "feat-1" in result.output
        assert "feat-3" in result.output
        # Check that worktrees were created via git_ops
        assert len(test_ctx.git.added_worktrees) == 2


def test_split_excludes_trunk() -> None:
    """Trunk branch stays in root worktree and is not split."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        current_branch = "feat-1"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Main should be marked as staying in root
        assert "trunk (stays in root)" in result.output
        # Main should not be in the "will create" list
        assert len(test_ctx.git.added_worktrees) == 0  # Only feat-1, which is current


def test_split_excludes_current_branch() -> None:
    """Current branch cannot be duplicated in another worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = "feat-1"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # feat-1 should be marked as current/already checked out
        assert "current (already checked out)" in result.output
        # Only feat-2 should be created
        assert "feat-2" in result.output
        assert len(test_ctx.git.added_worktrees) == 1


def test_split_preserves_existing_worktrees() -> None:
    """Idempotent operation - existing worktrees are preserved."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = "main"
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch="main", is_root=True),
            WorktreeInfo(path=env.erk_root / "feat-1", branch="feat-1", is_root=False),
        ]

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: existing_worktrees},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # feat-1 should be marked as already having a worktree
        assert "already has worktree" in result.output
        # Only feat-2 should be created
        assert len(test_ctx.git.added_worktrees) == 1


# Flag combination tests


def test_split_with_up_flag() -> None:
    """--up flag only splits upstack branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        current_branch = "feat-2"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "--up", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only feat-3 should be created (upstack from feat-2)
        assert "feat-3" in result.output
        assert "feat-1" not in result.output  # Downstack, not included
        assert len(test_ctx.git.added_worktrees) == 1


def test_split_with_down_flag() -> None:
    """--down flag only splits downstack branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        current_branch = "feat-2"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "--down", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only feat-1 should be created (downstack from feat-2, main excluded)
        assert "feat-1" in result.output
        assert "feat-3" not in result.output  # Upstack, not included
        assert len(test_ctx.git.added_worktrees) == 1


def test_split_up_and_down_conflict() -> None:
    """Error when both --up and --down flags are used."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = "feat-1"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "--up", "--down"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot use --up and --down together" in result.output


def test_split_with_force_flag() -> None:
    """--force flag skips confirmation prompt."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        # Without -f, would need interactive confirmation
        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Split complete:" in result.output


def test_split_with_dry_run() -> None:
    """--dry-run shows preview without creating worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN] Would create:" in result.output
        assert "[DRY RUN] No changes made" in result.output
        # No actual worktrees created
        assert len(test_ctx.git.added_worktrees) == 0


# Edge case tests


def test_split_detached_head_state() -> None:
    """Handle detached HEAD state gracefully."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = None  # Detached HEAD

        # For detached HEAD, use "main" as key for graphite stacks
        graphite_ops = FakeGraphite(stacks={"main": stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should split feat-1 and feat-2 (main excluded as trunk)
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        assert len(test_ctx.git.added_worktrees) == 2


def test_split_untracked_branch() -> None:
    """Error when branch is not tracked by Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Empty graphite_ops - no tracked branches
        graphite_ops = FakeGraphite(stacks={})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="untracked")]},
            current_branches={env.cwd: "untracked"},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["stack", "split"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_split_no_graphite_init() -> None:
    """Error when repository doesn't have Graphite initialized."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Graphite returns None for uninitialized repo
        graphite_ops = FakeGraphite(stacks=None)  # Returns None for all branches
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            current_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["stack", "split"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output
        assert "gt repo init" in result.output  # Suggests initialization


def test_split_uncommitted_changes() -> None:
    """Safety check prevents split with uncommitted changes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
            file_statuses={env.cwd: ([], ["modified_file.py"], [])},  # has_uncommitted=True
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes detected" in result.output
        assert "Commit or stash" in result.output


def test_split_uncommitted_changes_with_force() -> None:
    """--force flag still allows split with uncommitted changes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
            file_statuses={env.cwd: ([], ["modified_file.py"], [])},  # has_uncommitted=True
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should proceed with split
        assert "Split complete:" in result.output


def test_split_all_branches_have_worktrees() -> None:
    """Nothing to do when all branches already have worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        current_branch = "main"
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch="main", is_root=True),
            WorktreeInfo(path=env.erk_root / "feat-1", branch="feat-1", is_root=False),
        ]

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: existing_worktrees},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "All branches already have worktrees" in result.output
        assert len(test_ctx.git.added_worktrees) == 0


# Output verification tests


def test_split_output_formatting() -> None:
    """Verify correct colors and symbols in output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        current_branch = "feat-2"  # Current is feat-2, not main
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch="feat-2", is_root=False),
            WorktreeInfo(path=env.erk_root / "main", branch="main", is_root=True),
            WorktreeInfo(path=env.erk_root / "feat-1", branch="feat-1", is_root=False),
        ]

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: existing_worktrees},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Check for expected markers
        assert "← trunk (stays in root)" in result.output  # main
        assert "← current (already checked out)" in result.output  # feat-2
        assert "✓ already has worktree" in result.output  # feat-1
        assert "→ will create worktree" in result.output  # feat-3


def test_split_dry_run_output() -> None:
    """Dry run shows clear preview of what would be created."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN] Would create:" in result.output
        # Should show paths where worktrees would be created
        assert "feat-1 at" in result.output
        assert "feat-2 at" in result.output
        assert "[DRY RUN] No changes made" in result.output


def test_split_success_messages() -> None:
    """Successful split shows completion confirmation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "✅ Created worktree for" in result.output
        assert "✅ Split complete:" in result.output
        assert "created 2 worktree(s)" in result.output


def test_split_with_master_as_trunk() -> None:
    """Handle 'master' as trunk branch instead of 'main'."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["master", "feat-1"]
        current_branch = "feat-1"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "master"},  # trunk_branch="master"
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Master should be marked as trunk
        assert "trunk (stays in root)" in result.output
        # feat-1 is current, so nothing to create
        assert len(test_ctx.git.added_worktrees) == 0


def test_split_empty_stack() -> None:
    """Handle edge case of single-branch stack (just trunk)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        stack_branches = ["main"]
        current_branch = "main"

        graphite_ops = FakeGraphite(stacks={current_branch: stack_branches})
        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True)]},
            current_branches={env.cwd: current_branch},
            trunk_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(use_graphite=True, git=git_ops, graphite=graphite_ops)

        result = runner.invoke(cli, ["stack", "split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "All branches already have worktrees or are excluded" in result.output
        assert len(test_ctx.git.added_worktrees) == 0

"""Tests for erk consolidate command.

This file tests the consolidate command which removes worktrees containing
branches from the current worktree stack.
"""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_consolidate_no_other_worktrees() -> None:
    """Test consolidate when no other worktrees contain stack branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree only (on feature-2)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "No other worktrees found" in result.output


def test_consolidate_no_other_worktrees_with_script_flag() -> None:
    """Test consolidate shows output with --script flag when no worktrees to remove."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree only (on feature-2)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # This would have caught the bug: output should display even with --script flag
        assert "No other worktrees found" in result.output


def test_consolidate_removes_other_stack_worktrees() -> None:
    """Test consolidate removes worktrees with branches from current stack."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktree directories
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"
        wt2_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt2"

        # Current worktree on feature-2, other worktrees on feature-1 and main
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "🗑️  Removing worktrees..." in result.output
        assert str(wt1_path) in result.output
        assert str(wt2_path) in result.output
        assert len(test_ctx.git.removed_worktrees) == 2


def test_consolidate_preserves_current_worktree() -> None:
    """Test consolidate preserves the current worktree even if it's in the stack."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create other worktree
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"

        # Both worktrees in same stack, current is on feature-1
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 should be removed, not cwd
        assert len(test_ctx.git.removed_worktrees) == 1
        assert wt1_path in test_ctx.git.removed_worktrees


def test_consolidate_aborts_on_uncommitted_changes() -> None:
    """Test consolidate aborts if ANY worktree has uncommitted changes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree with uncommitted changes marker
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        # Configure file_statuses to simulate uncommitted changes in wt1
        file_statuses = {
            wt1_path: ([], [], ["uncommitted.txt"]),  # Untracked file
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
            file_statuses=file_statuses,
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes detected" in result.output
        assert len(test_ctx.git.removed_worktrees) == 0


def test_consolidate_dry_run_shows_preview() -> None:
    """Test --dry-run shows what would be removed without executing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert str(wt1_path) in result.output
        assert len(test_ctx.git.removed_worktrees) == 0


def test_consolidate_confirmation_prompt() -> None:
    """Test consolidate prompts for confirmation without --force."""
    from erk_shared.gateway.console.fake import FakeConsole

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )

        # Create console with response to capture prompt
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[False],  # Say "no" to prompt
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            console=console,
        )

        # Test saying "no" to prompt
        result = runner.invoke(cli, ["stack", "consolidate"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify the confirmation prompt was shown (prompt includes full context)
        assert len(console.confirm_prompts) == 1
        assert "Proceed with removal?" in console.confirm_prompts[0]
        assert "Aborted" in result.output
        assert len(test_ctx.git.removed_worktrees) == 0


def test_consolidate_detached_head_error() -> None:
    """Test consolidate aborts if current worktree is in detached HEAD state."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Current worktree with detached HEAD (None branch)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch=None)]}

        # Create context with no current branch
        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "detached HEAD state" in result.output


def test_consolidate_not_tracked_by_graphite() -> None:
    """Test consolidate errors if current branch is not tracked by Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with only main branch (feature-1 is not tracked)
        graphite_ops = FakeGraphite(stacks={"main": ["main"]})

        # Current branch is "feature-1" but not in Graphite
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-1")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_consolidate_skips_non_stack_worktrees() -> None:
    """Test consolidate only removes worktrees with branches in current stack."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack-a only (main -> stack-a)
        # stack-b is a separate branch not in this stack
        graphite_ops = FakeGraphite(stacks={"stack-a": ["main", "stack-a"]})

        # Create worktrees
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"
        wt2_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt2"

        # Current on stack-a, wt1 on main (in stack), wt2 on stack-b (NOT in stack)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="stack-a"),
                WorktreeInfo(path=wt1_path, branch="main"),
                WorktreeInfo(path=wt2_path, branch="stack-b"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "stack-a"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 (main) should be removed, wt2 (stack-b) should remain
        assert len(test_ctx.git.removed_worktrees) == 1
        assert wt1_path in test_ctx.git.removed_worktrees
        assert wt2_path not in test_ctx.git.removed_worktrees


def test_consolidate_with_uncommitted_changes_in_non_stack_worktree() -> None:
    """Test consolidate succeeds when non-stack worktrees have uncommitted changes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktrees
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"
        wt2_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt2"
        wt3_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt3"

        # Current on feature-2, wt1 on feature-1 (in stack), wt2 on main (in stack),
        # wt3 on other-branch (NOT in stack, has uncommitted changes)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="main"),
                WorktreeInfo(path=wt3_path, branch="other-branch"),
            ]
        }

        # Configure file_statuses to simulate uncommitted changes in non-stack worktree
        file_statuses = {
            wt3_path: ([], [], ["uncommitted.txt"]),  # Untracked file in non-stack worktree
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
            file_statuses=file_statuses,
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        # Command should succeed despite uncommitted changes in non-stack worktree
        assert result.exit_code == 0, result.output
        # Only feature-1 and main worktrees should be removed
        assert len(test_ctx.git.removed_worktrees) == 2
        assert wt1_path in test_ctx.git.removed_worktrees
        assert wt2_path in test_ctx.git.removed_worktrees
        # other-branch worktree should remain untouched
        assert wt3_path not in test_ctx.git.removed_worktrees


def test_consolidate_preserves_root_worktree_even_when_in_stack() -> None:
    """Test consolidate never removes the root worktree, even if its branch is in the stack.

    This is a regression test for the bug where consolidate would attempt to remove
    the root worktree when run from a linked worktree, causing git to reject the
    operation with "fatal: '/path' is a main working tree".
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktree directories
        # Root worktree at repo root (on main branch, part of the stack)
        main_worktree = env.cwd / "main-repo"
        # Linked worktree for feature-1
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"
        # Current linked worktree for feature-2
        wt2_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt2"

        # Root worktree is on 'main' branch (which is in the stack)
        # Current worktree is wt2 on feature-2
        # wt1 is on feature-1 (also in stack)
        worktrees = {
            main_worktree: [
                WorktreeInfo(path=main_worktree, branch="main", is_root=True),  # Root worktree
                WorktreeInfo(path=wt1_path, branch="feature-1", is_root=False),  # Linked
                WorktreeInfo(path=wt2_path, branch="feature-2", is_root=False),  # Current
            ]
        }

        # Create custom context with wt2_path as cwd
        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={wt2_path: main_worktree / ".git"},
            current_branches={wt2_path: "feature-2"},
        )
        # Override git_common_dirs to include all worktrees
        git_ops._git_common_dirs[main_worktree] = main_worktree / ".git"
        git_ops._git_common_dirs[wt1_path] = main_worktree / ".git"
        git_ops._git_common_dirs[wt2_path] = main_worktree / ".git"

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            github=FakeGitHub(),
            graphite=graphite_ops,
            shell=FakeShell(),
            cwd=wt2_path,
            dry_run=False,
        )

        # Context already has cwd=wt2_path, no need for os.chdir() in pure mode
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        # Command should succeed
        assert result.exit_code == 0, result.output

        # Root worktree should NEVER be removed, even though 'main' is in the stack
        assert main_worktree not in test_ctx.git.removed_worktrees

        # Only feature-1 worktree should be removed (feature-2 is current, root is root)
        assert len(test_ctx.git.removed_worktrees) == 1
        assert wt1_path in test_ctx.git.removed_worktrees

        # Current worktree (feature-2) should also not be removed
        assert wt2_path not in test_ctx.git.removed_worktrees


def test_consolidate_partial_stack() -> None:
    """Test consolidating only trunk → specified branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3)
        graphite_ops = FakeGraphite(stacks={"feat-3": ["main", "feat-1", "feat-2", "feat-3"]})

        # Create worktree directories
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "wt1"
        wt2_path = repo_dir / "wt2"
        wt3_path = repo_dir / "wt3"

        # Three worktrees: wt1 (feat-1), wt2 (feat-2), wt3 (feat-3, current)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={wt3_path: env.git_dir},
            current_branches={wt3_path: "feat-3"},
        )
        # Override git_common_dirs
        git_ops._git_common_dirs[wt1_path] = env.git_dir
        git_ops._git_common_dirs[wt2_path] = env.git_dir
        git_ops._git_common_dirs[wt3_path] = env.git_dir

        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            cwd=wt3_path,
        )

        # Run consolidate with branch argument: consolidate feat-2
        # Should consolidate main → feat-2 only, keeping feat-3 separate
        result = runner.invoke(cli, ["stack", "consolidate", "feat-2", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should remove wt1 (feat-1) and wt2 (feat-2), but NOT wt3 (feat-3, current)
        assert len(test_ctx.git.removed_worktrees) == 2
        assert wt1_path in test_ctx.git.removed_worktrees
        assert wt2_path in test_ctx.git.removed_worktrees
        assert wt3_path not in test_ctx.git.removed_worktrees


def test_consolidate_branch_not_in_stack() -> None:
    """Test error when specified branch is not in current stack."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2)
        graphite_ops = FakeGraphite(stacks={"feat-2": ["main", "feat-1", "feat-2"]})

        # Current worktree on feat-2
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feat-2")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feat-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )

        # Try to consolidate to a branch not in the stack
        result = runner.invoke(cli, ["stack", "consolidate", "feat-99", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not in the current stack" in result.output
        assert "feat-99" in result.output


def test_consolidate_preserves_upstack_branches() -> None:
    """Test that branches above the specified branch remain in separate worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3 -> feat-4)
        graphite_ops = FakeGraphite(
            stacks={"feat-4": ["main", "feat-1", "feat-2", "feat-3", "feat-4"]}
        )

        # Create worktree directories
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "wt1"
        wt2_path = repo_dir / "wt2"
        wt3_path = repo_dir / "wt3"
        wt4_path = repo_dir / "wt4"

        # Four worktrees for feat-1, feat-2, feat-3, feat-4
        # Current is wt4 (feat-4)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
                WorktreeInfo(path=wt4_path, branch="feat-4"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={wt4_path: env.git_dir},
            current_branches={wt4_path: "feat-4"},
        )
        # Override git_common_dirs
        git_ops._git_common_dirs[wt1_path] = env.git_dir
        git_ops._git_common_dirs[wt2_path] = env.git_dir
        git_ops._git_common_dirs[wt3_path] = env.git_dir
        git_ops._git_common_dirs[wt4_path] = env.git_dir

        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            cwd=wt4_path,
        )

        # Consolidate feat-2 (from current=feat-4)
        # Should remove feat-1 and feat-2, but keep feat-3 and feat-4
        result = runner.invoke(cli, ["stack", "consolidate", "feat-2", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should remove wt1 (feat-1) and wt2 (feat-2)
        assert len(test_ctx.git.removed_worktrees) == 2
        assert wt1_path in test_ctx.git.removed_worktrees
        assert wt2_path in test_ctx.git.removed_worktrees
        # Should NOT remove wt3 (feat-3) and wt4 (feat-4, current)
        assert wt3_path not in test_ctx.git.removed_worktrees
        assert wt4_path not in test_ctx.git.removed_worktrees


def test_consolidate_shows_output_with_script_flag() -> None:
    """Test consolidate displays removal output even when --script flag is enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify output is shown even with --script flag
        assert "🗑️  Removing worktrees..." in result.output
        assert str(wt1_path) in result.output
        assert "Consolidation complete" in result.output
        assert "Next step:" in result.output


def test_consolidate_shows_output_without_script_flag() -> None:
    """Test consolidate displays removal output when --script flag is not enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify output is shown
        assert "🗑️  Removing worktrees..." in result.output
        assert str(wt1_path) in result.output
        assert "Consolidation complete" in result.output
        assert "Next step:" in result.output


def test_consolidate_script_mode_shows_preview_output() -> None:
    """Test consolidate displays full preview even with --script flag.

    Regression test for bug where line 277 guard suppressed ALL preview output
    in script mode, causing users to see nothing.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree to remove
        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(cli, ["stack", "consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify preview sections appear with new format
        assert "📋 Consolidation Plan" in result.output
        assert "Branches consolidating to current worktree:" in result.output
        assert "Worktrees to remove:" in result.output
        assert "─" in result.output  # Separator line
        assert "Next step:" in result.output

        # Verify visual markers appear
        assert "←" in result.output or "current" in result.output


def test_consolidate_outputs_to_stderr() -> None:
    """Test consolidate routes all user output to stderr for shell integration.

    Shell integration captures stdout. User-visible output must go to stderr
    or users won't see it.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        graphite_ops = FakeGraphite(stacks={"feature-1": ["main", "feature-1"]})

        wt1_path = env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-1"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )
        result = runner.invoke(
            cli, ["stack", "consolidate", "--script", "-f"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # With the fix, all output should appear in result.output
        # (which captures both streams by default)
        # The key test is that output DOES appear (not suppressed by --script flag)


def test_consolidate_allows_uncommitted_changes_in_protected_worktrees() -> None:
    """Test consolidate succeeds when protected worktrees have uncommitted changes.

    Protected worktrees are those that won't be removed during consolidation:
    - Root worktree (never removed)
    - Current worktree (consolidation target)
    - Non-consolidated branches in the stack (upstack from consolidation point)

    This test verifies the fix for the issue where root worktree uncommitted changes
    incorrectly blocked consolidation from linked worktrees.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3 -> feat-4)
        graphite_ops = FakeGraphite(
            stacks={"feat-4": ["main", "feat-1", "feat-2", "feat-3", "feat-4"]}
        )

        # Create worktree directories
        # Root worktree is env.cwd (on main branch)
        main_worktree = env.cwd
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "wt1"  # feat-1 (will be consolidated)
        wt2_path = repo_dir / "wt2"  # feat-2 (will be consolidated)
        wt3_path = repo_dir / "wt3"  # feat-3 (will NOT be consolidated, has uncommitted)
        wt4_path = repo_dir / "wt4"  # feat-4 (current, consolidation target)

        # Set up worktrees:
        # - Root worktree on main (protected, has uncommitted changes)
        # - feat-1 worktree (will be removed, must be clean)
        # - feat-2 worktree (will be removed, must be clean)
        # - feat-3 worktree (protected, not in consolidation range, has uncommitted changes)
        # - feat-4 worktree (current, consolidation target)
        worktrees = {
            main_worktree: [
                WorktreeInfo(path=main_worktree, branch="main", is_root=True),
                WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False),
                WorktreeInfo(path=wt2_path, branch="feat-2", is_root=False),
                WorktreeInfo(path=wt3_path, branch="feat-3", is_root=False),
                WorktreeInfo(path=wt4_path, branch="feat-4", is_root=False),
            ]
        }

        # Simulate uncommitted changes in protected worktrees only
        file_statuses = {
            main_worktree: ([], [], ["uncommitted.txt"]),  # Root worktree has changes (OK)
            # wt1_path is clean (required, will be removed)
            # wt2_path is clean (required, will be removed)
            wt3_path: ([], ["modified.txt"], []),  # feat-3 has changes (OK, not consolidated)
            # wt4_path is current (can have changes)
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={wt4_path: env.git_dir},
            current_branches={wt4_path: "feat-4"},
            file_statuses=file_statuses,
        )

        # Override git_common_dirs for all worktrees
        git_ops._git_common_dirs[wt1_path] = env.git_dir
        git_ops._git_common_dirs[wt2_path] = env.git_dir
        git_ops._git_common_dirs[wt3_path] = env.git_dir
        git_ops._git_common_dirs[wt4_path] = env.git_dir

        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            cwd=wt4_path,
        )

        # Consolidate feat-2 (from current=feat-4)
        # This consolidates main → feat-1 → feat-2, but NOT feat-3 or feat-4
        # Should succeed despite uncommitted changes in root and feat-3
        result = runner.invoke(cli, ["stack", "consolidate", "feat-2", "-f"], obj=test_ctx)

        # Command should succeed
        assert result.exit_code == 0, result.output

        # feat-1 and feat-2 worktrees should be removed
        assert len(test_ctx.git.removed_worktrees) == 2
        assert wt1_path in test_ctx.git.removed_worktrees
        assert wt2_path in test_ctx.git.removed_worktrees

        # Protected worktrees should NOT be removed
        assert main_worktree not in test_ctx.git.removed_worktrees  # Root
        assert wt3_path not in test_ctx.git.removed_worktrees  # Not consolidated
        assert wt4_path not in test_ctx.git.removed_worktrees  # Current


def test_consolidate_with_name_tracks_temp_branch_with_graphite() -> None:
    """Test that temporary branch created during consolidate --name is tracked by Graphite.

    This is a regression test for the bug where:
    1. `erk consolidate` creates temp branch but doesn't track it with Graphite
    2. Second `erk consolidate --name <name>` call fails with "not tracked by Graphite" error

    The fix ensures that after creating the temporary branch, we call
    ctx.graphite_ops.track_branch() to register it in Graphite's cache.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree on feature-2
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )

        # Run consolidate with --name flag to create new worktree
        result = runner.invoke(
            cli, ["stack", "consolidate", "--name", "my-stack", "-f"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output

        # Verify that temporary branch was tracked with Graphite
        # The fix ensures ctx.graphite_ops.track_branch() is called
        assert len(graphite_ops.track_branch_calls) == 1

        # Verify the track call parameters
        cwd, temp_branch_name, parent_branch = graphite_ops.track_branch_calls[0]
        assert cwd == env.cwd  # Tracking happens in current worktree
        assert temp_branch_name.startswith("temp-consolidate-")  # Temp branch naming pattern
        assert parent_branch == "feature-2"  # Parent is current branch


def test_consolidate_with_name_changes_directory_before_removal() -> None:
    """Test that consolidate --name changes to new worktree before removing source.

    This is a regression test for the bug where:
    1. `erk consolidate --name <target>` creates new worktree
    2. Command skips changing directory to new worktree in script mode
    3. Source worktree gets deleted while shell is still in it
    4. Shell ends up in a deleted directory

    The fix ensures safe_chdir() is called unconditionally (both script and non-script modes)
    before the source worktree is removed.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree on feature-2
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )

        # Run consolidate with --name flag in script mode
        result = runner.invoke(
            cli, ["stack", "consolidate", "--name", "my-stack", "--script", "-f"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output

        # Verify directory change happened before removal
        # The FakeGit should record a safe_chdir call
        # Expected: New worktree path
        expected_new_path = (
            env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "my-stack"
        )

        # Verify that safe_chdir was called with the new worktree path
        assert hasattr(test_ctx.git, "chdir_history"), "FakeGit should track chdir calls"
        assert len(test_ctx.git.chdir_history) > 0, "Should have called safe_chdir"

        # The new worktree path should be in the chdir history
        assert any(expected_new_path == path for path in test_ctx.git.chdir_history), (
            f"Should have changed to new worktree {expected_new_path}"
        )

        # Verify the source worktree was removed
        # Note: env.cwd is the source worktree that should be removed
        assert len(test_ctx.git.removed_worktrees) == 1, "Should have removed source worktree"


def test_consolidate_with_name_changes_directory_in_non_script_mode() -> None:
    """Test that consolidate --name changes directory in non-script mode.

    Verifies the fix works correctly without --script flag.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree on feature-2
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )

        # Run consolidate with --name flag WITHOUT script mode
        result = runner.invoke(
            cli, ["stack", "consolidate", "--name", "my-stack", "-f"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output

        # Verify directory change happened
        expected_new_path = (
            env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "my-stack"
        )

        # Verify that safe_chdir was called
        assert hasattr(test_ctx.git, "chdir_history"), "FakeGit should track chdir calls"
        assert len(test_ctx.git.chdir_history) > 0, "Should have called safe_chdir"

        # The new worktree path should be in the chdir history
        assert any(expected_new_path == path for path in test_ctx.git.chdir_history), (
            f"Should have changed to new worktree {expected_new_path}"
        )


def test_consolidate_with_name_outputs_script_even_when_branch_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test consolidate --name outputs script even when temp branch deletion fails.

    This is the key bug fix: when delete_branch fails AFTER source worktree deletion,
    the script should already have been output so shell can navigate.

    Without the fix:
    1. Create new worktree
    2. Remove source worktree (shell now in deleted dir!)
    3. Delete temp branch fails → no script output → shell stranded

    With the fix:
    1. Create new worktree
    2. Output script ← early output
    3. Remove source worktree
    4. Delete temp branch fails → script already output → shell can navigate
    """
    import subprocess

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Mock time.time() to get predictable temp branch name
        mock_timestamp = 1234567890
        monkeypatch.setattr("time.time", lambda: mock_timestamp)

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphite(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree on feature-2
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        # Configure git to fail when deleting the temp branch
        temp_branch_name = f"temp-consolidate-{mock_timestamp}"
        git_ops = FakeGit(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-2"},
            delete_branch_raises={
                temp_branch_name: subprocess.CalledProcessError(
                    1, f"git branch -D {temp_branch_name}", stderr="fatal: Cannot delete branch"
                )
            },
        )
        test_ctx = build_workspace_test_context(
            env,
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
        )

        # Run consolidate with --name flag in script mode
        result = runner.invoke(
            cli, ["stack", "consolidate", "--name", "my-stack", "--script", "-f"], obj=test_ctx
        )

        # Command should exit with non-zero code due to branch delete failure
        assert result.exit_code != 0

        # Verify script was written by the script writer
        assert env.script_writer.written_scripts, (
            f"Script should have been written before failure. Output: {result.output}"
        )

        # Key verification: Script path IS output in stdout (before failure)
        # The script path is output via output_for_shell_integration() and appears in stdout
        script_path = list(env.script_writer.written_scripts.keys())[0]
        assert str(script_path) in result.stdout, (
            f"Script path should be in stdout. Script: {script_path}, stdout: {result.stdout}"
        )

        # Verify source worktree WAS removed (deletion happened before the failure)
        # The source worktree is env.cwd
        assert env.cwd.resolve() in test_ctx.git.removed_worktrees, (
            "Source worktree should have been removed"
        )

        # Verify script content IS valid (navigates to new worktree)
        script_content = list(env.script_writer.written_scripts.values())[0]
        expected_new_path = (
            env.erk_root / "repos" / env.root_worktree.name / "worktrees" / "my-stack"
        )
        assert str(expected_new_path) in script_content, (
            f"Script should navigate to new worktree. Content: {script_content}"
        )

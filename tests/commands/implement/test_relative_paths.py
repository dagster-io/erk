"""Tests for relative path preservation in implement command."""

import os
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_interactive_mode_preserves_relative_path_from_subdirectory() -> None:
    """Verify interactive mode passes relative path when run from subdirectory.

    When user runs `erk implement #42` from worktree/src/lib/, the relative path
    'src/lib' should be captured and passed to execute_interactive so that Claude
    can start in the corresponding subdirectory of the new worktree.
    """
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a subdirectory structure in the worktree
        subdir = env.cwd / "src" / "lib"
        subdir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # Include worktree info so compute_relative_path_in_worktree works
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)

        # Build context with cwd set to the subdirectory
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, claude_executor=executor, cwd=subdir
        )

        # Change to subdirectory before invoking command
        os.chdir(subdir)

        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, ["#42"], obj=ctx, env={"ERK_SHELL": "zsh"})

        assert result.exit_code == 0

        # Verify execute_interactive was called with relative path
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath, model, _ = executor.interactive_calls[0]
        assert dangerous is False
        assert command == "/erk:system:impl-execute"
        # The relative path from worktree root to src/lib should be passed
        assert target_subpath == Path("src/lib")
        assert model is None


def test_interactive_mode_no_relative_path_from_worktree_root() -> None:
    """Verify interactive mode passes None when run from worktree root.

    When user runs `erk implement #42` from the worktree root itself,
    no relative path should be passed (target_subpath=None).
    """
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        # Run from worktree root (default in erk_isolated_fs_env)
        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, ["#42"], obj=ctx, env={"ERK_SHELL": "zsh"})

        assert result.exit_code == 0

        # Verify target_subpath is None when at worktree root
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath, model, _ = executor.interactive_calls[0]
        assert target_subpath is None
        assert model is None


def test_interactive_mode_preserves_relative_path_from_plan_file() -> None:
    """Verify plan file mode also preserves relative path when run from subdirectory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a subdirectory structure
        subdir = env.cwd / "docs"
        subdir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        executor = FakeClaudeExecutor(claude_available=True)

        # Create plan file at worktree root
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        # Build context with cwd set to the subdirectory
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor, cwd=subdir)

        # Change to subdirectory before invoking command
        os.chdir(subdir)

        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, [str(plan_file)], obj=ctx, env={"ERK_SHELL": "zsh"})

        assert result.exit_code == 0

        # Verify execute_interactive was called with relative path
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath, model, _ = executor.interactive_calls[0]
        assert target_subpath == Path("docs")
        assert model is None

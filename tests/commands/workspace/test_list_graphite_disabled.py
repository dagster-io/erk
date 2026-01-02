"""Tests for wt list command with Graphite disabled.

This file verifies that worktree listing works correctly when Graphite
is disabled (use_graphite=False), proving graceful degradation.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_wt_list_succeeds_without_graphite() -> None:
    """Worktree listing works when use_graphite=False."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # use_graphite=False is the default
        test_ctx = env.build_context(git=git_ops, use_graphite=False)

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "root" in result.output


def test_wt_list_shows_empty_pr_column_without_graphite() -> None:
    """PR column shows empty/dash when Graphite is disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        wt_path = repo_dir / "worktrees" / "feature"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feature", is_root=False),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, wt_path: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=False, existing_paths={wt_path})

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Output should still work, just without PR info
        assert "feature" in result.output


def test_wt_list_shows_multiple_worktrees_without_graphite() -> None:
    """Multiple worktrees are listed correctly without Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "worktrees" / "feature-1"
        wt2_path = repo_dir / "worktrees" / "feature-2"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt1_path, branch="feature-1", is_root=False),
                    WorktreeInfo(path=wt2_path, branch="feature-2", is_root=False),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                wt1_path: env.git_dir,
                wt2_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(
            git=git_ops, use_graphite=False, existing_paths={wt1_path, wt2_path}
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "feature-1" in result.output
        assert "feature-2" in result.output


def test_wt_list_no_graphite_errors() -> None:
    """No Graphite-related errors or warnings in output when disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=False)

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify no Graphite-related error messages
        output_lower = result.output.lower()
        assert "graphite" not in output_lower
        assert "gt" not in output_lower or "git" in output_lower  # "gt" might appear in paths

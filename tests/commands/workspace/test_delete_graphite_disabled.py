"""Tests for wt delete command with Graphite disabled.

This file verifies that worktree deletion works correctly when Graphite
is disabled (use_graphite=False), proving graceful degradation.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.cli_helpers import assert_cli_success
from tests.test_utils.env_helpers import erk_inmem_env


def test_wt_delete_succeeds_without_graphite() -> None:
    """Worktree deletion works when use_graphite=False."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-feature"

        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # use_graphite=False is the default
        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            use_graphite=False,
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["wt", "delete", "test-feature", "-f"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert f"Deleted worktree: {wt}" in result.output


def test_wt_delete_with_branch_flag_uses_git() -> None:
    """--branch flag uses git branch -d when Graphite is disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-branch"

        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            use_graphite=False,
            existing_paths={wt},
        )

        result = runner.invoke(
            cli,
            ["wt", "delete", "test-branch", "--branch", "-f"],
            obj=test_ctx,
        )

        # Should succeed and use git branch -d (not gt delete)
        assert_cli_success(result)
        assert "feature" in git_ops.deleted_branches


def test_wt_delete_all_flag_works_without_graphite() -> None:
    """--all flag works when Graphite is disabled (PR/branch deletion via git)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-feature"

        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature-branch")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            use_graphite=False,
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["wt", "delete", "test-feature", "-a", "-f"], obj=test_ctx)

        assert_cli_success(result)
        # --all implies --branch, so branch should be deleted via git
        assert "feature-branch" in git_ops.deleted_branches


def test_wt_delete_no_graphite_errors() -> None:
    """No Graphite-related errors when deleting with Graphite disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "foo"

        git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="foo")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            use_graphite=False,
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["wt", "delete", "foo", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # No Graphite errors in output
        assert "GraphiteDisabledError" not in result.output
        assert "requires Graphite" not in result.output

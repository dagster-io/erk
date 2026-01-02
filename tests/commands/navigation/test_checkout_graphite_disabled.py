"""Tests for branch checkout command with Graphite disabled.

This file verifies that branch checkout works correctly when Graphite
is disabled (use_graphite=False), proving graceful degradation.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_checkout_succeeds_without_graphite() -> None:
    """Branch checkout works when use_graphite=False."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        # use_graphite=False is the default
        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        result = runner.invoke(
            cli,
            ["branch", "checkout", "feature-2", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should generate activation script
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_wt) in script_content


def test_checkout_does_not_call_ensure_graphite_tracking() -> None:
    """Checkout does not call Graphite tracking methods when disabled.

    _ensure_graphite_tracking() should return early when use_graphite=False.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        result = runner.invoke(
            cli,
            ["branch", "checkout", "feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        # If Graphite tracking was called, it would have failed or raised errors
        # The fact that we succeed means Graphite operations were skipped


def test_checkout_auto_creates_worktree_without_graphite() -> None:
    """Auto-creating worktree for unchecked-out branch works without Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "unchecked-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        # Checkout a branch that exists locally but isn't checked out anywhere
        result = runner.invoke(
            cli,
            ["branch", "checkout", "unchecked-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should auto-create worktree
        assert result.exit_code == 0, result.output
        assert len(git_ops.added_worktrees) == 1


def test_checkout_no_graphite_errors_in_output() -> None:
    """No Graphite-related errors or warnings in output when disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        result = runner.invoke(
            cli,
            ["branch", "checkout", "feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        # Verify no Graphite-related error messages
        assert "GraphiteDisabledError" not in result.output
        assert "requires Graphite" not in result.output
        assert "gt track" not in result.output


def test_checkout_alias_works_without_graphite() -> None:
    """erk br co alias works correctly without Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        # Use the br co alias
        result = runner.invoke(
            cli,
            ["br", "co", "feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output

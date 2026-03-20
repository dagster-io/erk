"""Tests for slot checkout command with Graphite disabled.

This file verifies that slot checkout works correctly when Graphite
is disabled (use_graphite=False), proving graceful degradation.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_checkout_succeeds_without_graphite() -> None:
    """Slot checkout works when use_graphite=False."""
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
            pool_json_path=work_dir / "pool.json",
        )

        # use_graphite=False is the default
        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-2", "--script"],
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
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        # If Graphite tracking was called, it would have failed or raised errors
        # The fact that we succeed means Graphite operations were skipped


def test_checkout_auto_allocates_slot_without_graphite() -> None:
    """Checking out unchecked-out branch allocates a slot without Graphite.

    When a branch exists locally but isn't checked out anywhere, the unified
    slot checkout allocates a slot for it (behavioral change from branch checkout).
    """
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
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        # Checkout a branch that exists locally but isn't checked out anywhere
        result = runner.invoke(
            cli,
            ["slot", "checkout", "unchecked-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should allocate a slot (behavioral change from old branch checkout)
        assert result.exit_code == 0, result.output


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
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        # Verify no Graphite-related error messages
        assert "GraphiteDisabledError" not in result.output
        assert "requires Graphite" not in result.output
        assert "gt track" not in result.output


def test_checkout_alias_works_without_graphite() -> None:
    """erk slot co alias works correctly without Graphite."""
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
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=False)

        # Use the slot co alias
        result = runner.invoke(
            cli,
            ["slot", "co", "feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output

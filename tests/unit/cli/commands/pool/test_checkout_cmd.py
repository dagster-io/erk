"""Unit tests for pool checkout command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _create_test_assignment(
    slot_name: str,
    branch_name: str,
    worktree_path: Path,
) -> SlotAssignment:
    """Create a test assignment with current timestamp."""
    return SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=datetime.now(UTC).isoformat(),
        worktree_path=worktree_path,
    )


def test_pool_checkout_navigates_to_assigned_slot() -> None:
    """Test that pool checkout navigates to the correct worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create pool worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees with pool slot
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature-test", is_root=False),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with assignment
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Run pool checkout (without --script for user output mode)
        result = runner.invoke(
            cli, ["pool", "checkout", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        # Command exits with 0 even though it needs shell integration
        # The output should show the worktree info
        assert "pool slot" in result.output or "Shell integration" in result.output


def test_pool_checkout_branch_not_in_pool() -> None:
    """Test that pool checkout fails for branch not in pool."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create empty pool state
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pool", "checkout", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "not found in pool" in result.output
        assert "erk pool list" in result.output  # Hint to run pool list
        assert "erk pool assign" in result.output  # Hint to assign


def test_pool_checkout_no_pool_configured() -> None:
    """Test that pool checkout fails when no pool is configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Do NOT create pool.json

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pool", "checkout", "some-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No pool configured" in result.output


def test_pool_checkout_alias_co() -> None:
    """Test that 'erk pool co' works as alias for checkout."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create pool worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature-x", is_root=False),
            ]
        }

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-x", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Use "co" alias instead of "checkout"
        result = runner.invoke(
            cli, ["pool", "co", "feature-x"], obj=test_ctx, catch_exceptions=False
        )

        # Should work (either shows shell integration message or pool slot info)
        assert "pool slot" in result.output or "Shell integration" in result.output

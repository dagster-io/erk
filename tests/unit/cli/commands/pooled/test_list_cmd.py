"""Unit tests for pooled list command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pooled_list_empty() -> None:
    """Test that pooled list shows all slots as available when empty."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # All 4 slots should be shown
        assert "erk-managed-wt-01" in result.output
        assert "erk-managed-wt-02" in result.output
        assert "erk-managed-wt-03" in result.output
        assert "erk-managed-wt-04" in result.output
        # All should be available
        assert "(available)" in result.output


def test_pooled_list_with_assignments() -> None:
    """Test that pooled list shows assigned branches."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-populate pool state
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="feature-xyz",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=repo_dir / "worktrees" / "erk-managed-wt-01",
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Slot 1 should show assignment
        assert "feature-xyz" in result.output
        # Other slots should be available
        assert "erk-managed-wt-02" in result.output


def test_pooled_list_alias_ls() -> None:
    """Test that pooled ls alias works."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "ls"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "erk-managed-wt-01" in result.output

"""Unit tests for pooled unassign command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
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


def test_pooled_unassign_by_slot_name() -> None:
    """Test unassigning by slot name."""
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

        # Create initial pool state with an assignment
        worktree_path = repo.worktrees_dir / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "unassign", "erk-managed-wt-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "feature-test" in result.output
        assert "erk-managed-wt-01" in result.output

        # Verify assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0


def test_pooled_unassign_by_branch_name() -> None:
    """Test unassigning by branch name."""
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

        # Create initial pool state with an assignment
        worktree_path = repo.worktrees_dir / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "unassign", "feature-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "feature-branch" in result.output

        # Verify assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0


def test_pooled_unassign_not_found() -> None:
    """Test unassigning non-existent slot or branch shows error."""
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
            cli, ["pooled", "unassign", "nonexistent"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No assignment found" in result.output


def test_pooled_unassign_no_pool_configured() -> None:
    """Test unassigning when no pool is configured shows error."""
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

        # Do NOT create pool.json - simulates no pool configured

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "unassign", "something"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No pool configured" in result.output


def test_pooled_unassign_preserves_other_assignments() -> None:
    """Test that unassigning one slot preserves other assignments."""
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

        # Create pool state with two assignments
        wt_path_1 = repo.worktrees_dir / "erk-managed-wt-01"
        wt_path_1.mkdir(parents=True)
        wt_path_2 = repo.worktrees_dir / "erk-managed-wt-02"
        wt_path_2.mkdir(parents=True)

        assignment1 = _create_test_assignment("erk-managed-wt-01", "feature-a", wt_path_1)
        assignment2 = _create_test_assignment("erk-managed-wt-02", "feature-b", wt_path_2)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment1, assignment2),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Unassign first one
        result = runner.invoke(
            cli, ["pooled", "unassign", "feature-a"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify only one assignment remains
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-b"
        assert state.assignments[0].slot_name == "erk-managed-wt-02"

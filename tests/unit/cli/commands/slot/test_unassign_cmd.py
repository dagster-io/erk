"""Unit tests for slot unassign command."""

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


def test_slot_unassign_by_slot_name() -> None:
    """Test unassigning by slot name checks out placeholder branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees={env.cwd: env.build_worktrees("main")[env.cwd]},
            current_branches={env.cwd: "main", worktree_path: "feature-test"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-test"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create initial pool state with an assignment
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "unassign", "erk-managed-wt-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "feature-test" in result.output
        assert "erk-managed-wt-01" in result.output
        assert "Switched to placeholder branch" in result.output
        assert "erk wt co root" in result.output

        # Verify assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0

        # Verify placeholder branch was checked out
        assert (worktree_path, "__erk-slot-01-placeholder__") in git_ops.checked_out_branches

        # Verify placeholder branch was created from trunk
        assert (env.cwd, "__erk-slot-01-placeholder__", "main") in git_ops.created_branches


def test_slot_unassign_not_found() -> None:
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
        initial_state = PoolState.test()
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "unassign", "nonexistent"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No worktree found" in result.output


def test_slot_unassign_no_pool_configured() -> None:
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
            cli, ["slot", "unassign", "something"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No pool configured" in result.output


def test_slot_unassign_preserves_other_assignments() -> None:
    """Test that unassigning one slot preserves other assignments."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create pool state with two assignments
        wt_path_1 = repo_dir / "worktrees" / "erk-managed-wt-01"
        wt_path_1.mkdir(parents=True)
        wt_path_2 = repo_dir / "worktrees" / "erk-managed-wt-02"
        wt_path_2.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees={env.cwd: env.build_worktrees("main")[env.cwd]},
            current_branches={env.cwd: "main", wt_path_1: "feature-a", wt_path_2: "feature-b"},
            git_common_dirs={env.cwd: env.git_dir, wt_path_1: env.git_dir, wt_path_2: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        assignment1 = _create_test_assignment("erk-managed-wt-01", "feature-a", wt_path_1)
        assignment2 = _create_test_assignment("erk-managed-wt-02", "feature-b", wt_path_2)
        initial_state = PoolState.test(assignments=(assignment1, assignment2))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Unassign first one by slot name
        result = runner.invoke(
            cli, ["slot", "unassign", "erk-managed-wt-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify only one assignment remains
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-b"
        assert state.assignments[0].slot_name == "erk-managed-wt-02"


def test_slot_unassign_fails_with_uncommitted_changes() -> None:
    """Test unassigning fails when worktree has uncommitted changes."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees={env.cwd: env.build_worktrees("main")[env.cwd]},
            current_branches={env.cwd: "main", worktree_path: "feature-test"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-test"]},
            # Simulate uncommitted changes in the worktree
            file_statuses={worktree_path: ([], ["modified-file.py"], [])},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "unassign", "erk-managed-wt-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "uncommitted changes" in result.output

        # Verify assignment was NOT removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1

        # Verify no checkout happened
        assert len(git_ops.checked_out_branches) == 0


def test_slot_unassign_uses_existing_placeholder_branch() -> None:
    """Test unassigning uses existing placeholder branch without creating new one."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Placeholder branch already exists
        git_ops = FakeGit(
            worktrees={env.cwd: env.build_worktrees("main")[env.cwd]},
            current_branches={env.cwd: "main", worktree_path: "feature-test"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-test", "__erk-slot-01-placeholder__"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "unassign", "erk-managed-wt-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify placeholder branch was checked out
        assert (worktree_path, "__erk-slot-01-placeholder__") in git_ops.checked_out_branches

        # Verify NO branch was created (placeholder already existed)
        assert len(git_ops.created_branches) == 0

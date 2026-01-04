"""Unit tests for slot repair command."""

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


def test_slot_repair_no_pool_configured() -> None:
    """Test repair when no pool is configured shows error."""
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

        result = runner.invoke(cli, ["slot", "repair"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "No pool configured" in result.output


def test_slot_repair_no_stale_assignments() -> None:
    """Test repair when there are no stale assignments."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", worktree_path: "feature-test"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            # Mark path as existing
            existing_paths={worktree_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with a valid assignment (worktree exists)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "repair"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "No stale assignments found" in result.output

        # Verify state unchanged
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1


def test_slot_repair_removes_stale_with_force() -> None:
    """Test repair removes stale assignments with --force flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        # Do NOT create the directory - simulates stale assignment

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            # Path does NOT exist (not in existing_paths)
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with a stale assignment (worktree doesn't exist)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "repair", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Found 1 stale assignment" in result.output
        assert "erk-managed-wt-01" in result.output
        assert "feature-test" in result.output
        assert "Removed 1 stale assignment" in result.output

        # Verify assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0


def test_slot_repair_preserves_valid_assignments() -> None:
    """Test repair preserves valid assignments when removing stale ones."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create two worktree paths - one exists, one doesn't
        valid_wt_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        valid_wt_path.mkdir(parents=True)
        stale_wt_path = repo_dir / "worktrees" / "erk-managed-wt-02"
        # Do NOT create stale_wt_path

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", valid_wt_path: "feature-a"},
            git_common_dirs={env.cwd: env.git_dir, valid_wt_path: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={valid_wt_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with one valid and one stale assignment
        valid_assignment = _create_test_assignment("erk-managed-wt-01", "feature-a", valid_wt_path)
        stale_assignment = _create_test_assignment("erk-managed-wt-02", "feature-b", stale_wt_path)
        initial_state = PoolState.test(assignments=(valid_assignment, stale_assignment))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "repair", "-f"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Found 1 stale assignment" in result.output
        assert "erk-managed-wt-02" in result.output
        assert "feature-b" in result.output

        # Verify only stale assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].slot_name == "erk-managed-wt-01"
        assert state.assignments[0].branch_name == "feature-a"


def test_slot_repair_confirmation_required_without_force() -> None:
    """Test repair prompts for confirmation without --force flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        # Do NOT create the directory

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

        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Simulate user saying 'n' to confirmation
        result = runner.invoke(
            cli, ["slot", "repair"], obj=test_ctx, input="n\n", catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Found 1 stale assignment" in result.output
        assert "Aborted" in result.output

        # Verify assignment was NOT removed (user declined)
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1


def test_slot_repair_confirmation_yes() -> None:
    """Test repair proceeds when user confirms with 'y'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        # Do NOT create the directory

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

        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Simulate user saying 'y' to confirmation
        result = runner.invoke(
            cli, ["slot", "repair"], obj=test_ctx, input="y\n", catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Removed 1 stale assignment" in result.output

        # Verify assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0

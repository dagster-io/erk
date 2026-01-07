"""Unit tests for slot repair command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment
from erk_shared.gateway.repo_state.fake import FakeRepoLevelStateStore
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


def _build_worktree_info(path: Path, branch: str) -> WorktreeInfo:
    """Build WorktreeInfo for a slot worktree."""
    return WorktreeInfo(
        path=path,
        branch=branch,
        is_root=False,
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

        # Build worktrees list including the slot worktree in git registry
        base_worktrees = env.build_worktrees("main")
        slot_wt_info = _build_worktree_info(worktree_path, "feature-test")
        worktrees_with_slot = {env.cwd: base_worktrees[env.cwd] + [slot_wt_info]}

        git_ops = FakeGit(
            worktrees=worktrees_with_slot,
            current_branches={env.cwd: "main", worktree_path: "feature-test"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            # Mark path as existing
            existing_paths={worktree_path},
            # Branch exists in git
            branch_heads={"feature-test": "abc123"},
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
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        result = runner.invoke(cli, ["slot", "repair"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "No issues found" in result.output

        # Verify state unchanged
        assert repo_state_store.current_pool_state is not None
        assert len(repo_state_store.current_pool_state.assignments) == 1


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
            # Branch exists in git (only orphan-state issue, not missing-branch)
            branch_heads={"feature-test": "abc123"},
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
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        result = runner.invoke(
            cli, ["slot", "repair", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Found 1 repairable issue" in result.output
        assert "erk-managed-wt-01" in result.output
        assert "feature-test" in result.output
        assert "Removed 1 stale assignment" in result.output

        # Verify assignment was removed
        assert repo_state_store.current_pool_state is not None
        assert len(repo_state_store.current_pool_state.assignments) == 0


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

        # Build worktrees list including the valid slot worktree in git registry
        base_worktrees = env.build_worktrees("main")
        valid_slot_wt_info = _build_worktree_info(valid_wt_path, "feature-a")
        worktrees_with_slot = {env.cwd: base_worktrees[env.cwd] + [valid_slot_wt_info]}

        git_ops = FakeGit(
            worktrees=worktrees_with_slot,
            current_branches={env.cwd: "main", valid_wt_path: "feature-a"},
            git_common_dirs={env.cwd: env.git_dir, valid_wt_path: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={valid_wt_path},
            # Both branches exist in git
            branch_heads={"feature-a": "abc123", "feature-b": "def456"},
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
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        result = runner.invoke(cli, ["slot", "repair", "-f"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Found 1 repairable issue" in result.output
        assert "erk-managed-wt-02" in result.output
        assert "feature-b" in result.output

        # Verify only stale assignment was removed
        state = repo_state_store.current_pool_state
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
            # Branch exists in git
            branch_heads={"feature-test": "abc123"},
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
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        # Simulate user saying 'n' to confirmation
        result = runner.invoke(
            cli, ["slot", "repair"], obj=test_ctx, input="n\n", catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Found 1 repairable issue" in result.output
        assert "Aborted" in result.output

        # Verify assignment was NOT removed (user declined)
        assert repo_state_store.current_pool_state is not None
        assert len(repo_state_store.current_pool_state.assignments) == 1


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
            # Branch exists in git
            branch_heads={"feature-test": "abc123"},
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
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        # Simulate user saying 'y' to confirmation
        result = runner.invoke(
            cli, ["slot", "repair"], obj=test_ctx, input="y\n", catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Removed 1 stale assignment" in result.output

        # Verify assignment was removed
        assert repo_state_store.current_pool_state is not None
        assert len(repo_state_store.current_pool_state.assignments) == 0


def test_slot_repair_shows_branch_mismatch_info() -> None:
    """Test repair shows branch-mismatch issues with remediation suggestions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Git registry shows different branch than pool.json
        base_worktrees = env.build_worktrees("main")
        slot_wt_info = _build_worktree_info(worktree_path, "actual-branch")
        worktrees_with_slot = {env.cwd: base_worktrees[env.cwd] + [slot_wt_info]}

        git_ops = FakeGit(
            worktrees=worktrees_with_slot,
            current_branches={env.cwd: "main", worktree_path: "actual-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={worktree_path},
            # Both branches exist
            branch_heads={"expected-branch": "abc123", "actual-branch": "def456"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pool.json says expected-branch but git says actual-branch
        assignment = _create_test_assignment("erk-managed-wt-01", "expected-branch", worktree_path)
        initial_state = PoolState.test(assignments=(assignment,))
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        result = runner.invoke(cli, ["slot", "repair"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should show informational issue
        assert "requiring manual intervention" in result.output
        assert "branch-mismatch" in result.output
        assert "expected-branch" in result.output
        assert "actual-branch" in result.output
        # Should show remediation suggestions
        assert "erk slot unassign" in result.output
        assert "git checkout" in result.output
        # Should NOT prompt for repair (no repairable issues)
        assert "Remove" not in result.output

        # State should be unchanged
        assert repo_state_store.current_pool_state is not None
        assert len(repo_state_store.current_pool_state.assignments) == 1


def test_slot_repair_shows_both_repairable_and_informational() -> None:
    """Test repair shows both repairable and informational issues."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # One worktree with branch-mismatch (exists but wrong branch)
        mismatch_wt_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        mismatch_wt_path.mkdir(parents=True)

        # One worktree that doesn't exist (orphan-state, repairable)
        stale_wt_path = repo_dir / "worktrees" / "erk-managed-wt-02"
        # Do NOT create stale_wt_path

        # Git registry shows slot-01 with wrong branch, slot-02 not in registry
        base_worktrees = env.build_worktrees("main")
        mismatch_wt_info = _build_worktree_info(mismatch_wt_path, "actual-branch")
        worktrees_with_slot = {env.cwd: base_worktrees[env.cwd] + [mismatch_wt_info]}

        git_ops = FakeGit(
            worktrees=worktrees_with_slot,
            current_branches={env.cwd: "main", mismatch_wt_path: "actual-branch"},
            git_common_dirs={env.cwd: env.git_dir, mismatch_wt_path: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={mismatch_wt_path},
            branch_heads={
                "expected-branch": "abc123",
                "actual-branch": "def456",
                "stale-branch": "ghi789",
            },
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with both issues
        mismatch_assignment = _create_test_assignment(
            "erk-managed-wt-01", "expected-branch", mismatch_wt_path
        )
        stale_assignment = _create_test_assignment(
            "erk-managed-wt-02", "stale-branch", stale_wt_path
        )
        initial_state = PoolState.test(assignments=(mismatch_assignment, stale_assignment))
        repo_state_store = FakeRepoLevelStateStore(initial_pool_state=initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo, repo_state_store=repo_state_store)

        result = runner.invoke(cli, ["slot", "repair", "-f"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should show both types of issues
        assert "requiring manual intervention" in result.output
        assert "branch-mismatch" in result.output
        assert "Found 1 repairable issue" in result.output
        assert "erk-managed-wt-02" in result.output
        assert "Removed 1 stale assignment" in result.output

        # Only the stale assignment should be removed
        state = repo_state_store.current_pool_state
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].slot_name == "erk-managed-wt-01"

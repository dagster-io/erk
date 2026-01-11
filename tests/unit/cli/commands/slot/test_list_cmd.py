"""Unit tests for slot list command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_slot_list_empty() -> None:
    """Test that slot list shows all slots as available when empty."""
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

        result = runner.invoke(cli, ["slot", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # All 4 slots should be shown
        assert "erk-slot-01" in result.output
        assert "erk-slot-02" in result.output
        assert "erk-slot-03" in result.output
        assert "erk-slot-04" in result.output
        # All should show "available" status
        assert "available" in result.output


def test_slot_list_with_assignments() -> None:
    """Test that slot list shows assigned branches."""
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
        state = PoolState.test(
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-xyz",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=repo_dir / "worktrees" / "erk-slot-01",
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Slot 1 should show assignment
        assert "feature-xyz" in result.output
        # Other slots should be available
        assert "erk-slot-02" in result.output


def test_slot_list_alias_ls() -> None:
    """Test that slot ls alias works."""
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

        result = runner.invoke(cli, ["slot", "ls"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "erk-slot-01" in result.output


def test_slot_list_shows_reason_column() -> None:
    """Test that slot list shows Reason column with issue status."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", worktree_path: "feature-xyz"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-populate pool state with matching branch
        state = PoolState.test(
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-xyz",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Reason column should be shown
        assert "Reason" in result.output
        # When pool.json matches filesystem, healthy state shows "-" (no issue)


def test_slot_list_shows_dirty_for_uncommitted_changes() -> None:
    """Test that slot list shows 'dirty' for worktrees with uncommitted changes."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", worktree_path: "feature-xyz"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            file_statuses={worktree_path: (["staged.py"], [], [])},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-populate pool state with matching branch
        state = PoolState.test(
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-xyz",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Changes column should show "dirty"
        assert "dirty" in result.output
        # Other slots without changes should show "-"
        assert "Changes" in result.output


def test_slot_list_shows_exists_column() -> None:
    """Test that slot list shows Exists column indicating physical worktree presence."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory for slot 01 (exists physically)
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", worktree_path: "feature-xyz"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-populate pool state with assignment
        state = PoolState.test(
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-xyz",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Exists column header should be shown
        assert "Exists" in result.output
        # Slot 01 should show "yes" (physically exists)
        assert "yes" in result.output


def test_slot_list_healthy_when_branch_upstack_from_assigned() -> None:
    """Stacked branches should show healthy status, not branch-mismatch.

    When the actual branch is upstack from the assigned branch in the same
    Graphite stack, the slot should show as healthy (assigned), not as an error.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        # Worktree has child branch "feature-xyz-child"
        # but pool.json says it's assigned to parent "feature-xyz"
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", worktree_path: "feature-xyz-child"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        # Configure Graphite with a stack where child is upstack from parent
        # Stack: main -> feature-xyz -> feature-xyz-child
        graphite_ops = FakeGraphite(
            stacks={
                "feature-xyz": ["main", "feature-xyz", "feature-xyz-child"],
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-populate pool state with parent branch assignment
        state = PoolState.test(
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-xyz",  # Assigned to parent
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should show "assigned" (healthy), not "error"
        assert "assigned" in result.output
        # Should NOT show branch-mismatch error
        assert "branch-mismatch" not in result.output

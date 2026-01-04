"""Unit tests for slots list command."""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_slots_list_empty_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that slots list shows all slots as empty when no worktrees exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Isolate Path.home() to prevent flakiness in parallel test runs
        monkeypatch.setattr("pathlib.Path.home", lambda: env.cwd.parent)

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

        result = runner.invoke(cli, ["slots", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # All 4 slots should be shown
        assert "erk-managed-wt-01" in result.output
        assert "erk-managed-wt-02" in result.output
        assert "erk-managed-wt-03" in result.output
        assert "erk-managed-wt-04" in result.output
        # All should be empty
        assert "empty" in result.output


def test_slots_list_with_assigned_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that slots list shows assigned branch for assigned slots."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Isolate Path.home() to prevent flakiness in parallel test runs
        monkeypatch.setattr("pathlib.Path.home", lambda: env.cwd.parent)

        repo_dir = env.setup_repo_structure()
        worktrees_dir = repo_dir / "worktrees"

        # Create the worktree directory
        slot_path = worktrees_dir / "erk-managed-wt-01"
        slot_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", slot_path: "feature-xyz"},
            git_common_dirs={env.cwd: env.git_dir, slot_path: env.git_dir},
            existing_paths={env.cwd, env.git_dir, slot_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=worktrees_dir,
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-populate pool state with assignment
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="feature-xyz",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=slot_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slots", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Assigned slot should show branch and assigned status
        assert "feature-xyz" in result.output
        assert "assigned" in result.output
        # Other slots should be empty
        assert "erk-managed-wt-02" in result.output


def test_slots_list_with_available_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that slots list shows available status for unassigned worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Isolate Path.home() to prevent flakiness in parallel test runs
        monkeypatch.setattr("pathlib.Path.home", lambda: env.cwd.parent)

        repo_dir = env.setup_repo_structure()
        worktrees_dir = repo_dir / "worktrees"

        # Create a worktree directory with placeholder branch (not assigned)
        slot_path = worktrees_dir / "erk-managed-wt-02"
        slot_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main", slot_path: "__erk-slot-02-placeholder__"},
            git_common_dirs={env.cwd: env.git_dir, slot_path: env.git_dir},
            existing_paths={env.cwd, env.git_dir, slot_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=worktrees_dir,
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slots", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Slot 2 should be available with placeholder branch
        assert "__erk-slot-02-placeholder__" in result.output
        assert "available" in result.output


def test_slots_list_mixed_states(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test slots list with mix of assigned, available, and empty slots."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Isolate Path.home() to prevent flakiness in parallel test runs
        monkeypatch.setattr("pathlib.Path.home", lambda: env.cwd.parent)

        repo_dir = env.setup_repo_structure()
        worktrees_dir = repo_dir / "worktrees"

        # Slot 1: assigned
        slot1_path = worktrees_dir / "erk-managed-wt-01"
        slot1_path.mkdir(parents=True)

        # Slot 2: available (has placeholder branch)
        slot2_path = worktrees_dir / "erk-managed-wt-02"
        slot2_path.mkdir(parents=True)

        # Slots 3-4: empty (don't exist)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={
                env.cwd: "main",
                slot1_path: "my-feature",
                slot2_path: "__erk-slot-02-placeholder__",
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                slot1_path: env.git_dir,
                slot2_path: env.git_dir,
            },
            existing_paths={env.cwd, env.git_dir, slot1_path, slot2_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=worktrees_dir,
            pool_json_path=repo_dir / "pool.json",
        )

        # Only slot 1 is assigned
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="my-feature",
                    assigned_at="2025-01-03T10:30:00+00:00",
                    worktree_path=slot1_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slots", "list"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should have all three states
        assert "assigned" in result.output
        assert "available" in result.output
        assert "empty" in result.output
        # Feature branch should be shown for slot 1
        assert "my-feature" in result.output


def test_slots_list_alias_ls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that slots ls alias works."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Isolate Path.home() to prevent flakiness in parallel test runs
        monkeypatch.setattr("pathlib.Path.home", lambda: env.cwd.parent)

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

        result = runner.invoke(cli, ["slots", "ls"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "erk-managed-wt-01" in result.output

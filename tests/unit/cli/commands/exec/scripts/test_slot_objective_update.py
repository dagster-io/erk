"""Tests for slot-objective-update exec command.

Tests the command that updates the current slot's last_objective_issue in pool.json.
"""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.slot_objective_update import slot_objective_update
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_slot_objective_update_updates_objective_in_slot() -> None:
    """Test updates objective_issue when cwd is a slot worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={worktree_path: "feature-branch"},
            git_common_dirs={worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=worktree_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with slot that has no objective
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_issue=None),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=worktree_path, git=git_ops, repo=repo)

        result = runner.invoke(
            slot_objective_update,
            ["--objective-issue=456"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["slot_name"] == "erk-slot-01"
        assert data["objective_issue"] == 456

        # Verify pool.json was updated
        updated_state = load_pool_state(repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.slots) == 1
        assert updated_state.slots[0].last_objective_issue == 456


def test_slot_objective_update_overwrites_existing_objective() -> None:
    """Test overwrites existing objective_issue when set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={worktree_path: "feature-branch"},
            git_common_dirs={worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=worktree_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with slot that has existing objective
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_issue=123),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=worktree_path, git=git_ops, repo=repo)

        result = runner.invoke(
            slot_objective_update,
            ["--objective-issue=789"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective_issue"] == 789

        # Verify pool.json was updated (old value 123 replaced with 789)
        updated_state = load_pool_state(repo.pool_json_path)
        assert updated_state is not None
        assert updated_state.slots[0].last_objective_issue == 789


def test_slot_objective_update_returns_null_when_not_in_slot() -> None:
    """Test returns null when cwd is not in a pool slot worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a different worktree not in the pool
        regular_worktree = repo_dir / "worktrees" / "feature-foo"
        regular_worktree.mkdir(parents=True)

        # Create slot worktree
        slot_worktree = repo_dir / "worktrees" / "erk-slot-01"
        slot_worktree.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={regular_worktree: "feature-foo"},
            git_common_dirs={regular_worktree: env.git_dir},
        )

        repo = RepoContext(
            root=regular_worktree,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with a different slot
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_issue=123),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="other-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=slot_worktree,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=regular_worktree, git=git_ops, repo=repo)

        result = runner.invoke(
            slot_objective_update,
            ["--objective-issue=999"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["slot_name"] is None
        assert data["objective_issue"] is None
        assert data["message"] == "Not in a slot worktree"

        # Verify pool.json was NOT modified
        unchanged_state = load_pool_state(repo.pool_json_path)
        assert unchanged_state is not None
        assert unchanged_state.slots[0].last_objective_issue == 123


def test_slot_objective_update_returns_null_when_no_pool_json() -> None:
    """Test returns null when pool.json doesn't exist."""
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

        # Don't create pool.json

        test_ctx = env.build_context(cwd=env.cwd, git=git_ops, repo=repo)

        result = runner.invoke(
            slot_objective_update,
            ["--objective-issue=123"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["slot_name"] is None
        assert data["objective_issue"] is None


def test_slot_objective_update_with_explicit_slot_name() -> None:
    """Test updates objective when --slot-name is explicitly provided."""
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

        # Create pool.json with slot
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(
                SlotInfo(name="erk-slot-01", last_objective_issue=None),
                SlotInfo(name="erk-slot-02", last_objective_issue=None),
            ),
            assignments=(),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=env.cwd, git=git_ops, repo=repo)

        result = runner.invoke(
            slot_objective_update,
            ["--objective-issue=555", "--slot-name=erk-slot-02"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["slot_name"] == "erk-slot-02"
        assert data["objective_issue"] == 555

        # Verify pool.json was updated for slot-02 only
        updated_state = load_pool_state(repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.slots) == 2
        # slot-01 should be unchanged
        assert updated_state.slots[0].name == "erk-slot-01"
        assert updated_state.slots[0].last_objective_issue is None
        # slot-02 should be updated
        assert updated_state.slots[1].name == "erk-slot-02"
        assert updated_state.slots[1].last_objective_issue == 555


def test_slot_objective_update_detects_nested_path() -> None:
    """Test detects slot when cwd is nested within a slot worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        # Create nested directory within the worktree
        nested_path = worktree_path / "src" / "subdir"
        nested_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={nested_path: "feature-branch"},
            git_common_dirs={nested_path: env.git_dir},
        )

        repo = RepoContext(
            root=nested_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with slot
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_issue=None),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=nested_path, git=git_ops, repo=repo)

        result = runner.invoke(
            slot_objective_update,
            ["--objective-issue=321"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["slot_name"] == "erk-slot-01"
        assert data["objective_issue"] == 321

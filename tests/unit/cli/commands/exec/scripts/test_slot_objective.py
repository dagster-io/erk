"""Tests for slot-objective exec command.

Tests the command that looks up the current slot's last_objective_issue from pool.json.
"""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.slot_objective import slot_objective
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    save_pool_state,
)
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_slot_objective_returns_objective_when_in_slot() -> None:
    """Test returns objective_issue when cwd is a slot worktree with objective set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
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

        # Create pool.json with slot that has objective
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-managed-wt-01", last_objective_issue=123),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=worktree_path, git=git_ops, repo=repo)

        result = runner.invoke(slot_objective, obj=test_ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["objective_issue"] == 123
        assert data["slot_name"] == "erk-managed-wt-01"


def test_slot_objective_returns_null_when_slot_has_no_objective() -> None:
    """Test returns null objective when slot exists but has no objective set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
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
            slots=(SlotInfo(name="erk-managed-wt-01", last_objective_issue=None),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=worktree_path, git=git_ops, repo=repo)

        result = runner.invoke(slot_objective, obj=test_ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["objective_issue"] is None
        assert data["slot_name"] == "erk-managed-wt-01"


def test_slot_objective_returns_null_when_not_in_slot() -> None:
    """Test returns null when cwd is not in a pool slot worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a different worktree not in the pool
        regular_worktree = repo_dir / "worktrees" / "feature-foo"
        regular_worktree.mkdir(parents=True)

        # Create slot worktree
        slot_worktree = repo_dir / "worktrees" / "erk-managed-wt-01"
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
            slots=(SlotInfo(name="erk-managed-wt-01", last_objective_issue=123),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="other-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=slot_worktree,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(cwd=regular_worktree, git=git_ops, repo=repo)

        result = runner.invoke(slot_objective, obj=test_ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["objective_issue"] is None
        assert data["slot_name"] is None


def test_slot_objective_returns_null_when_no_pool_json() -> None:
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

        result = runner.invoke(slot_objective, obj=test_ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["objective_issue"] is None
        assert data["slot_name"] is None

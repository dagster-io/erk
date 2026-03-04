"""Tests for erk br co (branch checkout) command."""

import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.branch import branch_group
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Fixed timestamp for test Plan objects
TEST_PLAN_TIMESTAMP = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)


def test_checkout_succeeds_when_graphite_not_enabled() -> None:
    """Test branch checkout works when Graphite is not enabled (graceful degradation)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-branch"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Graphite is NOT enabled - use GraphiteDisabled sentinel
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli, ["br", "co", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed with graceful degradation (no Graphite tracking prompt)
        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        # Should not show Graphite error
        assert "requires Graphite" not in result.output


def test_checkout_succeeds_when_graphite_not_installed() -> None:
    """Test branch checkout works when Graphite CLI is not installed (graceful degradation)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-branch"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Graphite not installed - use GraphiteDisabled with NOT_INSTALLED reason
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli, ["br", "co", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed with graceful degradation (no Graphite tracking prompt)
        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        # Should not show Graphite error
        assert "requires Graphite" not in result.output


# --- Slot allocation tests ---


def test_branch_checkout_creates_slot_assignment_by_default() -> None:
    """Test that branch checkout creates a slot assignment by default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "feature-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Assigned feature-branch to erk-slot-01" in result.output

        # Verify pool state was persisted
        state = load_pool_state(env.repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-branch"
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_branch_checkout_no_slot_skips_assignment() -> None:
    """Test that --no-slot creates worktree without slot assignment."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "no-slot-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/no-slot-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--no-slot", "no-slot-branch"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Should NOT have slot assignment message
        assert "Assigned" not in result.output

        # Verify worktree was created using branch name, not slot name
        assert len(git.added_worktrees) == 1
        worktree_path = Path(git.added_worktrees[0][0])
        assert "erk-slot" not in worktree_path.name

        # Verify NO pool state was created
        state = load_pool_state(env.repo.pool_json_path)
        assert state is None


def test_branch_checkout_reuses_inactive_slot() -> None:
    """Test that branch checkout reuses an existing inactive slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Pre-create worktree directory for the slot
        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # Configure FakeGit with the existing slot worktree but no assignment
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "reuse-slot-branch"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="__erk-slot-01-br-stub__"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
        )

        # Create pool state with initialized slot but no assignment
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01"),),
            assignments=(),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "reuse-slot-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Assigned reuse-slot-branch to erk-slot-01" in result.output

        # Verify checkout_branch was called (reusing existing worktree)
        assert len(git.checked_out_branches) == 1
        checkout_path, checkout_branch = git.checked_out_branches[0]
        assert checkout_path == slot_worktree_path
        assert checkout_branch == "reuse-slot-branch"

        # Verify add_worktree was NOT called (reused existing)
        assert len(git.added_worktrees) == 0


def test_branch_checkout_creates_tracking_branch_for_remote() -> None:
    """Test that checkout creates a tracking branch for a remote-only branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # remote-branch not local yet
            remote_branches={env.cwd: ["origin/main", "origin/remote-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "remote-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "creating local tracking branch" in result.output
        assert "Assigned remote-branch to erk-slot-01" in result.output

        # Verify fetch and tracking branch creation
        assert ("origin", "remote-branch") in git.fetched_branches
        assert ("remote-branch", "origin/remote-branch") in git.created_tracking_branches


def test_branch_checkout_force_unassigns_oldest() -> None:
    """Test that --force unassigns the oldest slot when pool is full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Pre-create worktree directory for the slot
        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # Configure FakeGit with existing slot worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "force-branch"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="old-branch"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
        )

        # Create a full pool (1 slot, 1 assignment)
        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=slot_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        ctx = build_workspace_test_context(env, git=git, local_config=local_config)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "--force", "force-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Unassigned" in result.output
        assert "old-branch" in result.output
        assert "Assigned force-branch to erk-slot-01" in result.output

        # Verify checkout_branch was called (reusing slot)
        assert len(git.checked_out_branches) == 1
        checkout_path, checkout_branch = git.checked_out_branches[0]
        assert checkout_path == slot_worktree_path
        assert checkout_branch == "force-branch"

        # Verify new state
        state = load_pool_state(env.repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "force-branch"


def test_branch_checkout_pool_full_no_force_fails() -> None:
    """Test that pool-full without --force fails in non-interactive mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Pre-create worktree directory for the slot
        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # Configure FakeGit
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-branch", "blocked-branch"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="existing-branch"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
        )

        # Create a full pool
        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="existing-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=slot_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        ctx = build_workspace_test_context(env, git=git, local_config=local_config)

        # CliRunner runs in non-interactive mode by default
        result = runner.invoke(branch_group, ["checkout", "blocked-branch"], obj=ctx)

        assert result.exit_code == 1
        assert "Pool is full" in result.output


def test_branch_checkout_nonexistent_branch_fails() -> None:
    """Test that checking out a non-existent branch fails with helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},  # no-such-branch doesn't exist
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(branch_group, ["checkout", "no-such-branch"], obj=ctx)

        assert result.exit_code == 1
        assert "does not exist" in result.output
        assert "erk wt create --branch no-such-branch" in result.output


def test_branch_checkout_already_assigned_returns_existing() -> None:
    """Test that checking out an already-assigned branch returns existing slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Pre-create worktree directory for the slot
        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # Configure FakeGit with existing slot worktree already checked out to target branch
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "already-assigned"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="already-assigned"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
            current_branches={slot_worktree_path: "already-assigned"},
        )

        # Create pool state with the branch already assigned
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="already-assigned",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=slot_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, existing_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "already-assigned"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Should NOT show "Assigned" because branch was already assigned
        assert "Assigned already-assigned to" not in result.output
        # Should switch to existing worktree
        assert "erk-slot-01" in result.output or "Switched to" in result.output


# --- Stale pool.json state handling tests ---


def test_branch_checkout_stale_assignment_worktree_missing() -> None:
    """Test that stale assignment with missing worktree is removed and proceeds."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Worktree path in pool.json but doesn't exist on disk
        missing_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        # Note: NOT creating the directory - it's "missing"

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "stale-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Create pool state with assignment pointing to non-existent worktree
        stale_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="stale-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=missing_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, stale_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "stale-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Should warn about removing stale assignment
        assert "Removing stale assignment" in result.output
        assert "no longer exists" in result.output
        # Should proceed to assign to a slot
        assert "Assigned stale-branch to" in result.output


def test_branch_checkout_stale_assignment_wrong_branch() -> None:
    """Test that stale assignment with wrong branch is synced and target gets a new slot.

    With lazy tip sync, the pool state is corrected before allocation decisions.
    The assignment updates from target-branch to different-branch (what's actually
    checked out), and target-branch gets a fresh slot allocation.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # Git reports worktree has "different-branch" but pool.json says "target-branch"
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "target-branch", "different-branch"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="different-branch"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
            current_branches={slot_worktree_path: "different-branch"},
        )

        # Pool.json says target-branch is in slot-01
        stale_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="target-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=slot_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, stale_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "target-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Lazy tip sync corrects the assignment, then target-branch gets a new slot.
        # No "Fixing stale state" message — sync handles the mismatch transparently.
        # target-branch gets allocated to a new on-demand slot (slot-02)
        assert len(git.added_worktrees) == 1
        added_path, added_branch = git.added_worktrees[0]
        assert added_branch == "target-branch"
        assert "erk-slot-02" in str(added_path)


def test_branch_checkout_stale_assignment_wrong_branch_with_uncommitted_changes() -> None:
    """Test that stale assignment with uncommitted changes doesn't block target branch.

    With lazy tip sync, the assignment is corrected to reflect the actual branch
    (different-branch). The dirty slot-01 is now assigned to different-branch,
    and target-branch gets a fresh slot allocation — the uncommitted changes
    in slot-01 are irrelevant since we don't touch that slot.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # Git reports worktree has wrong branch AND uncommitted changes
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "target-branch", "different-branch"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="different-branch"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
            current_branches={slot_worktree_path: "different-branch"},
            file_statuses={slot_worktree_path: ([], ["dirty.py"], [])},  # Uncommitted
        )

        # Pool.json says target-branch is in slot-01
        stale_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="target-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=slot_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, stale_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "target-branch"], obj=ctx)

        # Sync corrects the assignment, target-branch gets a fresh slot.
        # Dirty slot-01 is untouched — no error.
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert len(git.added_worktrees) == 1
        added_path, added_branch = git.added_worktrees[0]
        assert added_branch == "target-branch"
        assert "erk-slot-02" in str(added_path)


def test_branch_checkout_internal_state_mismatch_allocated_but_not_checked_out() -> None:
    """Test that internal state mismatch error when branch allocated but no worktree has it.

    This tests the edge case where pool.json says a branch is assigned to a slot,
    but when we query git for worktrees, no worktree has that branch checked out.
    This indicates corrupted pool state that needs manual intervention.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

        # FakeGit needs to be configured so that:
        # 1. allocate_slot_for_branch succeeds (returns already_assigned=True)
        # 2. But find_worktrees_containing_branch returns empty list
        #
        # This happens when:
        # - Pool.json says branch is in slot
        # - Worktree directory exists
        # - Worktree reports SAME branch as pool.json (so validation passes)
        # - But list_worktrees returns worktree with DIFFERENT branch
        #
        # This simulates a race condition or corruption where the worktree state
        # changed between get_current_branch() and list_worktrees() calls.

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "orphaned-branch"]},
            # list_worktrees returns worktree with DIFFERENT branch
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="some-other-branch"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
            # But get_current_branch returns the branch from pool.json
            # This simulates the validation passing but worktree list being stale
            current_branches={slot_worktree_path: "orphaned-branch"},
        )

        # Pool.json says orphaned-branch is in slot-01
        stale_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="orphaned-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=slot_worktree_path,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, stale_state)

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(branch_group, ["checkout", "orphaned-branch"], obj=ctx)

        assert result.exit_code == 1
        assert "Internal state mismatch" in result.output
        assert "orphaned-branch" in result.output
        assert "no worktree has it checked out" in result.output


# --- --for-plan tests ---


def test_checkout_for_plan_creates_impl_folder() -> None:
    """Test that --for-plan resolves plan, creates branch, and sets up .impl/.

    When not in a pool slot and --new-slot is not set, the branch is checked out
    in the current worktree (no slot allocation).
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="500",
            title="Add feature",
            body="# Plan\nImplementation details",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/500",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"500": plan})

        # Draft-PR backend needs the branch to exist already
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "plan-500"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=plan_store)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "--for-plan", "500"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Created .erk/impl-context/ folder from plan #500" in result.output

        # No slot allocation should occur (checkout in current worktree)
        pool_state = load_pool_state(env.repo.pool_json_path)
        if pool_state is not None:
            assert len(pool_state.assignments) == 0

        # Verify branch-scoped impl folder was created in the CURRENT worktree (not a slot)
        impl_folder = env.cwd / ".erk" / "impl-context" / "plan-500"
        assert impl_folder.exists()
        assert (impl_folder / "plan.md").exists()
        assert (impl_folder / "ref.json").exists()


def test_checkout_for_plan_prints_activation_when_sync_status_fails() -> None:
    """Test that --for-plan checkout prints activation instructions even when sync status fails.

    Verifies the fix where display_sync_status errors could prevent activation
    instructions from being printed after --for-plan checkout. This happens when
    a newly-created tracking branch doesn't have upstream refs fully set up.

    Uses stack-in-place path (pool slot assigned) to test activation script output.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="600",
            title="Test activation output",
            body="# Plan\nTest plan content",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/600",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"600": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "plan-600"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
            ahead_behind_raises=RuntimeError("upstream tracking ref not set"),
        )

        # Pre-create pool state so the test exercises the stack-in-place path
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="existing-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, existing_state)

        ctx = build_workspace_test_context(env, git=git, plan_store=plan_store)

        # get_ahead_behind raises RuntimeError, simulating upstream tracking ref not set.
        # display_sync_status catches this internally, so activation instructions still print.
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "--for-plan", "600"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Created .erk/impl-context/ folder from plan #600" in result.output


def test_checkout_stacks_in_place_for_plan_outputs_activation_script() -> None:
    """Test that --for-plan in stack-in-place path outputs activation script for shell integration.

    When --for-plan is used and the current worktree is a pool slot (stack-in-place
    path), the activation script path is emitted to stdout so that shell integration
    can automatically execute it — no manual copy-paste step required.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="700",
            title="Stack in place activation",
            body="# Plan\nStack-in-place plan",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/700",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"700": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "plan-700"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Pre-create pool state with cwd assigned to a slot (triggers stack-in-place)
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="existing-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, existing_state)

        ctx = build_workspace_test_context(env, git=git, plan_store=plan_store)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "--for-plan", "700"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Stacked" in result.output
        assert "Created .erk/impl-context/ folder from plan #700" in result.output
        # Stack-in-place now auto-executes via script output (not interactive instructions)
        assert "To activate the worktree environment:" not in result.output
        # The activation script path is emitted to stdout for shell integration
        assert ".sh" in result.output


def test_checkout_for_plan_error_both_branch_and_for_plan() -> None:
    """Test that providing both BRANCH and --for-plan fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(
            branch_group, ["checkout", "my-branch", "--for-plan", "123"], obj=ctx
        )

        assert result.exit_code == 1
        assert "Cannot specify both BRANCH and --for-plan" in result.output


def test_checkout_for_plan_error_neither_branch_nor_for_plan() -> None:
    """Test that providing neither BRANCH nor --for-plan fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(branch_group, ["checkout"], obj=ctx)

        assert result.exit_code == 1
        assert "Must provide BRANCH argument or --for-plan option" in result.output


def test_checkout_new_slot_forces_new_allocation() -> None:
    """Test that --new-slot forces a new slot instead of stacking in place."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "new-feature"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Pre-create pool state with cwd assigned to a slot
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="existing-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, existing_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "--new-slot", "new-feature"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Assigned new-feature to" in result.output
        # Should NOT say "Stacked" or "in place"
        assert "Stacked" not in result.output
        assert "in place" not in result.output

        # Verify two assignments exist (original + new)
        state = load_pool_state(env.repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2


def test_checkout_new_slot_and_no_slot_fails() -> None:
    """Test that --new-slot and --no-slot together fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "some-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(
            branch_group, ["checkout", "--new-slot", "--no-slot", "some-branch"], obj=ctx
        )

        assert result.exit_code == 1
        assert "--new-slot and --no-slot cannot be used together" in result.output


def test_checkout_new_slot_errors_when_branch_exists_in_worktree() -> None:
    """Test that --new-slot errors when the branch is already checked out in a worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        if not slot_worktree_path.exists():
            slot_worktree_path.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-feature"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="existing-feature"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(
            branch_group, ["checkout", "--new-slot", "existing-feature"], obj=ctx
        )

        assert result.exit_code == 1
        assert "already checked out" in result.output
        assert "erk-slot-01" in result.output
        assert "Cannot create a new slot" in result.output


def test_checkout_new_slot_succeeds_when_branch_not_in_any_worktree() -> None:
    """Test that --new-slot succeeds when the branch is not already in a worktree.

    This verifies the normal --new-slot path still works (no regression).
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "fresh-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--new-slot", "fresh-branch"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Assigned fresh-branch to" in result.output


def test_checkout_without_new_slot_still_jumps_to_existing_worktree() -> None:
    """Test that checkout without --new-slot still jumps to existing worktree (no regression)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        if not slot_worktree_path.exists():
            slot_worktree_path.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-feature"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_worktree_path, branch="existing-feature"),
                ]
            },
            existing_paths={env.cwd, env.repo.worktrees_dir, slot_worktree_path},
        )
        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "existing-feature"], obj=ctx)

        # Should succeed without --new-slot
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Cannot create a new slot" not in result.output


def test_checkout_stacks_in_place_from_assigned_slot() -> None:
    """Test that checkout from assigned slot stacks in place by default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "target-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Pre-create pool state with cwd assigned to a slot
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="existing-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, existing_state)

        ctx = build_workspace_test_context(env, git=git)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(branch_group, ["checkout", "target-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Stacked target-branch in erk-slot-01 (in place)" in result.output

        # Verify assignment tip was updated
        state = load_pool_state(env.repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "target-branch"
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_checkout_stacks_in_place_for_plan_with_script() -> None:
    """Regression: --for-plan --script in stack-in-place path must checkout branch.

    Previously, _setup_impl_for_plan() called sys.exit(0) in script mode before
    _perform_checkout() could run, leaving the worktree on the old branch.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="500",
            title="Add feature",
            body="# Plan\nImplementation details",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/500",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"500": plan})

        branch = "plan-500"

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", branch]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Pre-create pool state with CWD assigned to a slot on "old-branch"
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, existing_state)

        ctx = build_workspace_test_context(env, git=git, plan_store=plan_store)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--for-plan", "500", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # The key assertion: branch was actually checked out
        assert len(git.checked_out_branches) >= 1
        checkout_path, checkout_branch = git.checked_out_branches[0]
        assert checkout_path == env.cwd
        assert checkout_branch == branch

        # Verify branch-scoped impl folder was created
        impl_folder = env.cwd / ".erk" / "impl-context" / "plan-500"
        assert impl_folder.exists()
        assert (impl_folder / "plan.md").exists()


def test_checkout_for_plan_planned_pr_stacks_on_base_ref() -> None:
    """--for-plan with planned_pr backend tracks with base_ref_name from plan metadata."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="600",
            title="Stack feature",
            body="# Plan\nStacking test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/600",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={"base_ref_name": "feature-parent"},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"600": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-parent", "plan-600"]},
            current_branches={env.cwd: "feature-parent"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, plan_store=plan_store, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--for-plan", "600", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify track_branch was called with base_ref_name from plan metadata
        assert len(graphite.track_branch_calls) == 1
        _repo_root, tracked_branch, parent = graphite.track_branch_calls[0]
        assert tracked_branch == "plan-600"
        assert parent == "feature-parent"


# --- Script mode error resilience tests ---


def test_checkout_script_mode_error_writes_error_script() -> None:
    """Test that --script mode outputs error script on stdout when command fails.

    When --new-slot --script fails because the branch is already checked out,
    stdout must contain a path to a valid error script (not be empty).
    This prevents ``source ""`` from producing a confusing shell error.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "existing-feature"

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="existing-feature", is_root=False),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(
            git=git,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli,
            ["br", "co", "--new-slot", "--script", "existing-feature"],
            obj=test_ctx,
        )

        assert result.exit_code == 1

        # stdout must contain a script path (not be empty)
        assert result.output.strip() != "", "stdout was empty — source would break"

        # The FakeScriptWriter should have written an error script
        last = env.script_writer.last_script
        assert last is not None
        assert "return 1" in last.content
        assert "erk error" in last.content


def test_checkout_script_mode_success_unaffected() -> None:
    """Regression test: --script success path is not broken by error handler."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-branch"

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(
            git=git,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli,
            ["br", "co", "--script", "feature-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        # stdout should have script path (non-empty)
        assert result.output.strip() != ""
        # The written script should NOT be an error script
        last = env.script_writer.last_script
        assert last is not None
        assert "return 1" not in last.content


def test_checkout_for_plan_planned_pr_falls_back_to_trunk_without_base_ref() -> None:
    """When plan metadata has no base_ref_name, falls back to trunk as parent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="601",
            title="Trunk feature",
            body="# Plan\nTrunk parent test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/601",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"601": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "plan-601"]},
            current_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, plan_store=plan_store, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--for-plan", "601", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify track_branch was called with trunk as parent
        assert len(graphite.track_branch_calls) == 1
        _repo_root, tracked_branch, parent = graphite.track_branch_calls[0]
        assert tracked_branch == "plan-601"
        assert parent == "main"


def test_checkout_for_plan_rebases_onto_stale_parent() -> None:
    """--for-plan with stacked parent rebases onto parent before gt track.

    When a plan has base_ref_name pointing to a non-trunk parent branch,
    the checkout should rebase onto origin/{parent} before calling gt track.
    This ensures gt track succeeds even if the parent advanced since plan-save.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="602",
            title="Stacked plan rebase",
            body="# Plan\nRebase test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/602",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={"base_ref_name": "feature-parent"},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"602": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-parent", "plan-602"]},
            current_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, plan_store=plan_store, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--for-plan", "602", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify rebase_onto was called with the parent branch
        assert len(git.rebase_onto_calls) == 1
        _cwd, target_ref = git.rebase_onto_calls[0]
        assert target_ref == "origin/feature-parent"

        # Verify track_branch was called with the parent (after rebase)
        assert len(graphite.track_branch_calls) == 1
        _repo_root, tracked_branch, parent = graphite.track_branch_calls[0]
        assert tracked_branch == "plan-602"
        assert parent == "feature-parent"


def test_checkout_for_plan_skips_rebase_for_trunk_parent() -> None:
    """--for-plan with trunk parent does not rebase, only tracks.

    When a plan has no base_ref_name (defaults to trunk), there's no need
    to rebase since the branch is already based on trunk.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="603",
            title="Trunk parent plan",
            body="# Plan\nNo rebase needed",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/603",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"603": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "plan-603"]},
            current_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, plan_store=plan_store, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--for-plan", "603", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # No rebase should happen for trunk parent
        assert len(git.rebase_onto_calls) == 0

        # Track should still be called with trunk
        assert len(graphite.track_branch_calls) == 1
        _repo_root, tracked_branch, parent = graphite.track_branch_calls[0]
        assert tracked_branch == "plan-603"
        assert parent == "main"


def test_checkout_for_plan_updates_stale_local_parent() -> None:
    """--for-plan syncs stale local parent branch with origin before gt track.

    When the parent branch exists locally but has diverged from origin
    (e.g., after squash/rebase via gt submit), the local ref should be
    updated to match origin so gt track sees consistent history.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            plan_identifier="604",
            title="Stale parent sync",
            body="# Plan\nStale parent test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/604",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={"base_ref_name": "feature-parent"},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"604": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-parent", "plan-604"]},
            current_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
            branch_heads={
                "feature-parent": "stale_local_sha",
                "origin/feature-parent": "fresh_remote_sha",
            },
        )

        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, plan_store=plan_store, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                branch_group, ["checkout", "--for-plan", "604", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify fetch was called for the parent branch
        assert ("origin", "feature-parent") in git.fetched_branches

        # Verify local ref was updated to match remote
        assert len(git.updated_refs) == 1
        _repo_root, branch, target_sha = git.updated_refs[0]
        assert branch == "feature-parent"
        assert target_sha == "fresh_remote_sha"

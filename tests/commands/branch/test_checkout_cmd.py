"""Tests for erk br co (branch checkout) command."""

import os
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
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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
            slots=(SlotInfo(name="erk-slot-01", last_objective_issue=None),),
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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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

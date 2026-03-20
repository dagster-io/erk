"""Unit tests for slot checkout command (unified checkout)."""

import os
from datetime import UTC, datetime
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.graphite import FakeGraphite
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Fixed timestamp for test Plan objects
TEST_PLAN_TIMESTAMP = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)


# --- Slot allocation tests (original slot checkout tests) ---


def test_slot_checkout_allocates_new_slot() -> None:
    """Test that slot checkout allocates a new slot for an existing branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-test"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "feature-test" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"


def test_slot_checkout_fails_if_branch_does_not_exist() -> None:
    """Test that slot checkout fails if branch does not exist locally or remotely."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "nonexistent"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "does not exist" in result.output


def test_slot_checkout_stack_in_place() -> None:
    """Test that slot checkout updates assignment tip when running inside a slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a pool state with cwd assigned as a slot
        initial_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-b"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify assignment was updated to new branch
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-b"
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_slot_checkout_new_slot_forces_allocation() -> None:
    """Test that --new-slot forces new slot allocation even inside a slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a pool state with cwd assigned as a slot
        initial_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "--new-slot", "feature-b"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "feature-b" in result.output

        # Verify we got a second slot (not in-place update)
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2


def test_slot_checkout_force_evicts_oldest() -> None:
    """Test that --force auto-unassigns oldest when pool is full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        from erk.cli.config import LoadedConfig

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "new-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "--force", "new-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "new-branch" in result.output

        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "new-branch"


def test_slot_checkout_pool_full_no_force_fails() -> None:
    """Test that pool full without --force fails in non-TTY mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        from erk.cli.config import LoadedConfig
        from tests.fakes.gateway.console import FakeConsole

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "new-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        console = FakeConsole(
            is_interactive=False, is_stdout_tty=None, is_stderr_tty=None, confirm_responses=None
        )
        test_ctx = env.build_context(
            git=git_ops, repo=repo, local_config=local_config, console=console
        )

        result = runner.invoke(
            cli, ["slot", "checkout", "new-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "Pool is full" in result.output
        assert "--force" in result.output


def test_slot_checkout_already_assigned_returns_existing() -> None:
    """Test that slot checkout returns existing assignment if branch already assigned."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="feature-a"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "feature-a"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, existing_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-a"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should navigate to existing worktree (branch found in worktree)
        assert "erk-slot-01" in result.output


def test_slot_checkout_reuses_inactive_worktree() -> None:
    """Test that slot checkout reuses an inactive worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="placeholder"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "placeholder"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pool has an initialized slot but no assignments -- slot is inactive
        state = PoolState.test(pool_size=4, assignments=())
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-a"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "feature-a" in result.output

        # Should have reused erk-slot-01 (not created erk-slot-02)
        updated = load_pool_state(repo.pool_json_path)
        assert updated is not None
        assert len(updated.assignments) == 1
        assert updated.assignments[0].slot_name == "erk-slot-01"


# --- Graphite disabled tests (migrated from branch checkout) ---


def test_checkout_succeeds_when_graphite_not_enabled() -> None:
    """Test slot checkout works when Graphite is not enabled (graceful degradation)."""
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

        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli, ["slot", "co", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        assert "requires Graphite" not in result.output


def test_checkout_succeeds_when_graphite_not_installed() -> None:
    """Test slot checkout works when Graphite CLI is not installed (graceful degradation)."""
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

        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli, ["slot", "co", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        assert "requires Graphite" not in result.output


# --- Unified checkout behavior tests (migrated and adapted from branch checkout) ---


def test_slot_checkout_allocates_slot_for_unchecked_branch() -> None:
    """Test that slot checkout allocates a slot when branch not in any worktree.

    Behavioral change from branch checkout: instead of checking out in the current
    worktree, slot checkout allocates a new pool slot.
    """
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
            result = runner.invoke(cli, ["slot", "checkout", "feature-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Should allocate a slot (not checkout in current worktree)
        state = load_pool_state(env.repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-branch"


def test_slot_checkout_creates_tracking_branch_for_remote() -> None:
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
            result = runner.invoke(cli, ["slot", "checkout", "remote-branch"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "creating local tracking branch" in result.output

        # Verify fetch and tracking branch creation
        assert ("origin", "remote-branch") in git.fetched_branches
        assert ("remote-branch", "origin/remote-branch") in git.created_tracking_branches


def test_slot_checkout_nonexistent_branch_fails() -> None:
    """Test that checking out a non-existent branch fails with helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(cli, ["slot", "checkout", "no-such-branch"], obj=ctx)

        assert result.exit_code == 1
        assert "does not exist" in result.output
        assert "erk wt create --branch no-such-branch" in result.output


def test_slot_checkout_navigates_to_already_assigned_worktree() -> None:
    """Test that checking out an already-assigned branch navigates to existing slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Pre-create worktree directory for the slot
        slot_worktree_path = env.repo.worktrees_dir / "erk-slot-01"
        slot_worktree_path.mkdir(parents=True)

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
            result = runner.invoke(cli, ["slot", "checkout", "already-assigned"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        # Should NOT show "Assigned" because branch was already in a worktree
        assert "Assigned already-assigned to" not in result.output
        # Should navigate to existing worktree
        assert "erk-slot-01" in result.output or "Switched to" in result.output


# --- --for-plan tests (migrated from branch checkout) ---


def test_checkout_for_plan_creates_impl_folder() -> None:
    """Test that --for-plan resolves plan, creates branch, and sets up .impl/."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            pr_identifier="500",
            title="[erk-pr] Add feature",
            body="# Plan\nImplementation details",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/500",
            labels=["erk-pr"],
            assignees=[],
            created_at=TEST_PLAN_TIMESTAMP,
            updated_at=TEST_PLAN_TIMESTAMP,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"500": plan})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "plan-500"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=plan_store)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["slot", "checkout", "--for-plan", "500"], obj=ctx)

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Created .erk/impl-context/ folder from PR #500" in result.output


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
            cli, ["slot", "checkout", "my-branch", "--for-plan", "123"], obj=ctx
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

        result = runner.invoke(cli, ["slot", "checkout"], obj=ctx)

        assert result.exit_code == 1
        assert "Must provide BRANCH argument or --for-plan option" in result.output


def test_checkout_for_plan_planned_pr_stacks_on_base_ref() -> None:
    """--for-plan with planned_pr backend tracks with base_ref_name from plan metadata."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            pr_identifier="600",
            title="[erk-pr] Stack feature",
            body="# Plan\nStacking test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/600",
            labels=["erk-pr"],
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
                cli, ["slot", "checkout", "--for-plan", "600", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify track_branch was called with base_ref_name from plan metadata
        assert len(graphite.track_branch_calls) == 1
        _repo_root, tracked_branch, parent = graphite.track_branch_calls[0]
        assert tracked_branch == "plan-600"
        assert parent == "feature-parent"


# --- Script mode error resilience tests ---


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
            ["slot", "co", "--script", "feature-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        assert result.output.strip() != ""
        last = env.script_writer.last_script
        assert last is not None
        assert "return 1" not in last.content


def test_checkout_for_plan_falls_back_to_trunk_without_base_ref() -> None:
    """When plan metadata has no base_ref_name, falls back to trunk as parent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            pr_identifier="601",
            title="[erk-pr] Trunk feature",
            body="# Plan\nTrunk parent test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/601",
            labels=["erk-pr"],
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
                cli, ["slot", "checkout", "--for-plan", "601", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify track_branch was called with trunk as parent
        assert len(graphite.track_branch_calls) == 1
        _repo_root, tracked_branch, parent = graphite.track_branch_calls[0]
        assert tracked_branch == "plan-601"
        assert parent == "main"


def test_checkout_for_plan_rebases_onto_stale_parent() -> None:
    """--for-plan with stacked parent rebases onto parent before gt track."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            pr_identifier="602",
            title="[erk-pr] Stacked plan rebase",
            body="# Plan\nRebase test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/602",
            labels=["erk-pr"],
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
                cli, ["slot", "checkout", "--for-plan", "602", "--script"], obj=ctx
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
    """--for-plan with trunk parent does not rebase, only tracks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            pr_identifier="603",
            title="[erk-pr] Trunk parent plan",
            body="# Plan\nNo rebase needed",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/603",
            labels=["erk-pr"],
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
                cli, ["slot", "checkout", "--for-plan", "603", "--script"], obj=ctx
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
    """--for-plan syncs stale local parent branch with origin before gt track."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        plan = Plan(
            pr_identifier="604",
            title="[erk-pr] Stale parent sync",
            body="# Plan\nStale parent test",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/604",
            labels=["erk-pr"],
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
                cli, ["slot", "checkout", "--for-plan", "604", "--script"], obj=ctx
            )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify fetch was called for the parent branch
        assert ("origin", "feature-parent") in git.fetched_branches

        # Verify local ref was updated to match remote
        assert len(git.updated_refs) == 1
        _repo_root, branch, target_sha = git.updated_refs[0]
        assert branch == "feature-parent"
        assert target_sha == "fresh_remote_sha"

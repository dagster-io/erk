"""Tests for erk br co (branch checkout) command."""

import os
from datetime import UTC, datetime
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.branch import branch_group
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


# --- Default checkout behavior tests ---


def test_branch_checkout_checks_out_in_current_worktree_by_default() -> None:
    """Test that branch checkout checks out in the current worktree by default (no slot)."""
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
        # No slot allocation — default is checkout in current worktree
        assert "Assigned" not in result.output

        # Verify checkout_branch was called on the root worktree (cwd)
        assert len(git.checked_out_branches) == 1
        checkout_path, checkout_branch = git.checked_out_branches[0]
        assert checkout_path == env.cwd
        assert checkout_branch == "feature-branch"

        # Verify NO pool state was created
        state = load_pool_state(env.repo.pool_json_path)
        assert state is None


def test_branch_checkout_creates_tracking_branch_for_remote() -> None:
    """Test that checkout creates a tracking branch for a remote-only branch.

    Default behavior is to checkout in the current worktree (no slot allocation).
    """
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
        # No slot allocation — default is checkout in current worktree
        assert "Assigned" not in result.output

        # Verify fetch and tracking branch creation
        assert ("origin", "remote-branch") in git.fetched_branches
        assert ("remote-branch", "origin/remote-branch") in git.created_tracking_branches


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


# --- --for-plan tests ---


def test_checkout_for_plan_creates_impl_folder() -> None:
    """Test that --for-plan resolves plan, creates branch, and sets up .impl/.

    The branch is checked out in the current worktree (no slot allocation).
    """
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
        assert "Created .erk/impl-context/ folder from PR #500" in result.output

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
            pr_identifier="600",
            title="[erk-pr] Test activation output",
            body="# Plan\nTest plan content",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/600",
            labels=["erk-pr"],
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
        assert "Created .erk/impl-context/ folder from PR #600" in result.output


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
                branch_group, ["checkout", "--for-plan", "600", "--script"], obj=ctx
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

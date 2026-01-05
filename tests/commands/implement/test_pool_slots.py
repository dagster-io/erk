"""Tests for pool slot behavior and regression tests in implement command.

Covers branch conflict/force flag, pre-existing slot directory, pool size config override,
uncommitted changes detection, and implementing from managed slots.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk.cli.config import LoadedConfig
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.metadata import format_plan_header_body
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Branch Conflict Tests


def test_implement_works_from_pool_slot() -> None:
    """Test that implement can be run from within a pool slot.

    Unlike the previous behavior which blocked running from within pool slots,
    the slot-first implementation allows this and assigns to a different slot.
    """
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Simulate running from within a pool slot by having the command work normally
        # (The old behavior would have blocked this with an error)
        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        # Should succeed - slot-first allows running from anywhere
        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1


def test_implement_force_flag_accepted() -> None:
    """Test that --force flag is accepted by the command.

    The --force flag allows auto-unassigning the oldest slot when the pool
    is full. This test verifies the flag is properly parsed and doesn't
    cause errors during normal operation.
    """
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Use --force flag (should work without issue when pool isn't full)
        result = runner.invoke(implement, ["#42", "--script", "--force"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output
        assert len(git.added_worktrees) == 1


# Pre-existing Slot Directory Tests


def test_implement_uses_checkout_when_slot_directory_exists() -> None:
    """Test that implement uses checkout_branch (not add_worktree) when slot dir exists.

    This is a regression test for a bug where `erk implement` would fail with
    "directory already exists" when:
    1. A managed slot directory exists on disk (from pool initialization)
    2. But find_inactive_slot() returns None (slot not tracked in pool state)

    The fix uses git.list_worktrees() to discover existing worktrees, so
    find_inactive_slot returns them. When an inactive slot is found,
    checkout_branch is used instead of add_worktree.
    """
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Pre-create the slot directory to simulate pool initialization
        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        # Configure git to know about the worktree via list_worktrees()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch=None, is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Pool state - find_inactive_slot now uses git.list_worktrees()
        # instead of state.slots, so we just need pool_size configured
        init_state = PoolState.test(pool_size=4)
        save_pool_state(env.repo.pool_json_path, init_state)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Key assertion: checkout_branch should be called (not add_worktree)
        # because the slot was returned by find_inactive_slot()
        assert len(git.checked_out_branches) == 1, (
            f"Expected 1 checkout_branch call, got {len(git.checked_out_branches)}"
        )
        assert len(git.added_worktrees) == 0, (
            f"Expected 0 add_worktree calls (slot was inactive), got {len(git.added_worktrees)}: "
            f"{git.added_worktrees}"
        )


# Pool Size Config Override Tests


def test_implement_respects_config_pool_size_over_stored_state() -> None:
    """Test that pool_size from config overrides the stored pool_size in pool.json.

    This is a regression test for a bug where:
    1. Pool state was created with pool_size=4 (the default)
    2. User configured pool_size=16 in config.toml
    3. When pool had 4 assignments, `erk implement` would fail with "Pool is full (4 slots)"
       even though config allowed 16 slots

    The fix ensures config's pool_size is used when loading existing pool state.
    """
    plan_issue = create_sample_plan_issue("99")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo = env.repo
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"99": plan_issue})

        # Create pool state with pool_size=4 and 4 assignments (full pool at old size)
        old_pool_size = 4
        assignments = tuple(
            SlotAssignment(
                slot_name=f"erk-managed-wt-{i:02d}",
                branch_name=f"existing-branch-{i}",
                assigned_at="2024-01-01T00:00:00+00:00",
                worktree_path=repo.worktrees_dir / f"erk-managed-wt-{i:02d}",
            )
            for i in range(1, old_pool_size + 1)
        )
        full_state = PoolState(
            version="1.0",
            pool_size=old_pool_size,  # Pool thinks max is 4
            slots=(),
            assignments=assignments,
        )
        save_pool_state(repo.pool_json_path, full_state)

        # Configure context with pool_size=16 (larger than stored)
        new_pool_size = 16
        local_config = LoadedConfig.test(pool_size=new_pool_size)
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, local_config=local_config
        )

        # Run implement - should succeed by using config's pool_size
        result = runner.invoke(implement, ["#99", "--script"], obj=ctx)

        # Should succeed, not fail with "Pool is full"
        assert result.exit_code == 0, f"Expected success but got: {result.output}"
        assert "Assigned" in result.output

        # Should have assigned to slot 5 (first available after slots 1-4)
        assert "erk-managed-wt-05" in result.output


# Uncommitted Changes Detection Tests


def test_implement_fails_with_uncommitted_changes_in_slot() -> None:
    """Test that implement fails with friendly error when slot has uncommitted changes.

    When a pre-existing slot directory has uncommitted changes that would be
    overwritten by git checkout, we should detect this BEFORE attempting checkout
    and provide actionable remediation steps instead of letting git fail with
    an ugly traceback.
    """
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Pre-create the slot directory with uncommitted changes
        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        # Configure git to know about the worktree and its dirty status
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # Configure the slot worktree to have uncommitted changes
            file_statuses={slot_dir: ([], ["modified_file.py"], [])},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch=None, is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Pool state - find_inactive_slot uses git.list_worktrees()
        init_state = PoolState.test(pool_size=4)
        save_pool_state(env.repo.pool_json_path, init_state)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        # Should fail with friendly error message
        assert result.exit_code != 0

        # Verify error message contains remediation options
        assert "uncommitted changes" in result.output
        assert "erk-managed-wt-01" in result.output
        assert "git stash" in result.output
        assert "git commit" in result.output
        assert "erk slot unassign" in result.output

        # Verify no worktree operations were attempted after the check
        assert len(git.added_worktrees) == 0
        assert len(git.checked_out_branches) == 0


# Tests for Implementing from Managed Slots (Maximize Parallelism)


def test_implement_from_managed_slot_gets_new_slot() -> None:
    """Test that implementing from within a managed slot gets a new slot.

    When running `erk implement` from within a managed slot:
    1. Gets a fresh slot for the new branch
    2. Parent branch stays assigned to its original slot
    3. New branch is stacked on current branch (for graphite)
    4. Pool state shows 2 assignments after implementation
    """
    plan_issue = create_sample_plan_issue("200")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create slot worktree directories
        slot1_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot1_dir.mkdir(parents=True)

        # Configure git to recognize the slot as a managed worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot1_dir: env.git_dir},
            local_branches={env.cwd: ["main", "existing-feature"]},
            default_branches={env.cwd: "main"},
            current_branches={slot1_dir: "existing-feature"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot1_dir, branch="existing-feature", is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"200": plan_issue})
        fake_graphite = FakeGraphite()

        # Create initial pool state with slot 01 assigned
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="existing-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot1_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        # Build context with cwd set to the slot directory
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            graphite=fake_graphite,
            use_graphite=True,
            cwd=slot1_dir,
        )

        # Run implement from within the slot
        result = runner.invoke(implement, ["#200", "--script"], obj=ctx)

        assert result.exit_code == 0, f"Expected success but got: {result.output}"

        # Verify a new branch was created
        assert len(git.created_branches) == 1

        # Verify the branch was tracked with the current branch as parent (stacking)
        assert len(fake_graphite.track_branch_calls) == 1
        _cwd, _new_branch, parent_branch = fake_graphite.track_branch_calls[0]
        assert parent_branch == "existing-feature"

        # Verify we got a NEW slot (slot 02), not reusing slot 01
        assert "erk-managed-wt-02" in result.output

        # Verify pool state has 2 assignments (parent keeps its slot)
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.assignments) == 2

        # Verify original slot still has original branch
        slot1_assignment = next(
            a for a in updated_state.assignments if a.slot_name == "erk-managed-wt-01"
        )
        assert slot1_assignment.branch_name == "existing-feature"


def test_implement_from_managed_slot_dry_run() -> None:
    """Test that dry-run mode shows new slot assignment when running from a slot."""
    plan_issue = create_sample_plan_issue("202")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main", "existing-feature"]},
            default_branches={env.cwd: "main"},
            current_branches={slot_dir: "existing-feature"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch="existing-feature", is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"202": plan_issue})

        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="existing-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            cwd=slot_dir,
        )

        result = runner.invoke(implement, ["#202", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Should show NEW slot assignment (slot 02), not same-slot stacking
        assert "erk-managed-wt-02" in result.output

        # Verify no changes were made
        assert len(git.created_branches) == 0
        assert len(git.checked_out_branches) == 0


def test_implement_not_from_slot_uses_new_slot() -> None:
    """Test that implementing from outside a managed slot uses a new slot.

    This verifies the normal behavior still works when NOT running from a slot.
    """
    plan_issue = create_sample_plan_issue("204")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create an existing slot assignment
        env.setup_repo_structure()
        slot1_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot1_dir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"204": plan_issue})

        # Create pool state with one existing assignment
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="other-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot1_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        # Run from the main worktree (not a slot)
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
        )

        result = runner.invoke(implement, ["#204", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Should assign to a NEW slot (slot 02)
        assert "erk-managed-wt-02" in result.output

        # Load pool state to verify
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.assignments) == 2  # Original + new


# Objective Propagation Tests


def _create_plan_with_objective(issue_number: str, objective_issue: int) -> Plan:
    """Create a plan issue with objective_issue in plan-header metadata."""
    body = format_plan_header_body(
        created_at="2024-01-01T00:00:00+00:00",
        created_by="testuser",
        objective_issue=objective_issue,
    )
    return Plan(
        plan_identifier=issue_number,
        title="Plan With Objective",
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )


def test_implement_from_issue_with_objective_propagates_to_slot() -> None:
    """Test that objective_issue from plan metadata is saved to slot."""
    plan_issue = _create_plan_with_objective("300", 42)

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"300": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#300", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output
        # Should show linked objective message
        assert "objective #42" in result.output

        # Verify slot was created with objective
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None

        # Find the slot that was assigned
        assigned_slot_name = updated_state.assignments[0].slot_name

        # Find the SlotInfo for that slot
        slot = next(
            (s for s in updated_state.slots if s.name == assigned_slot_name),
            None,
        )
        assert slot is not None
        assert slot.last_objective_issue == 42


def test_implement_from_issue_without_objective_does_not_create_slot_info() -> None:
    """Test that issue without objective doesn't add spurious SlotInfo."""
    plan_issue = create_sample_plan_issue("301")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"301": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#301", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output
        # Should NOT show linked objective message
        assert "objective" not in result.output.lower()

        # Verify no SlotInfo was created (only assignment exists)
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.assignments) == 1
        # No slots should have been added for objective tracking
        assigned_slot_name = updated_state.assignments[0].slot_name
        slot = next(
            (s for s in updated_state.slots if s.name == assigned_slot_name),
            None,
        )
        # Either no slot exists, or if it does, it has no objective
        if slot is not None:
            assert slot.last_objective_issue is None


def test_implement_from_file_does_not_propagate_objective() -> None:
    """Test that file-based implementation doesn't have objective."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "my-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output
        # Should NOT show linked objective message
        assert "objective" not in result.output.lower()

        # Verify no SlotInfo was created with objective
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None
        # No objective tracking for file-based plans
        assigned_slot_name = updated_state.assignments[0].slot_name
        slot = next(
            (s for s in updated_state.slots if s.name == assigned_slot_name),
            None,
        )
        # Either no slot or no objective
        if slot is not None:
            assert slot.last_objective_issue is None


def test_implement_objective_adds_new_slot_info() -> None:
    """Test that objective creates new SlotInfo when slot doesn't exist in slots list.

    When implementing on a fresh slot that has no prior SlotInfo, the implementation
    should create a new SlotInfo with the objective.
    """
    plan_issue = _create_plan_with_objective("302", 99)

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"302": plan_issue})

        # Slot-01 has an assignment (taking up slot 1)
        # Slot-02 is completely fresh (no SlotInfo, no dir)
        initial_slot1_assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="other-feature",
            assigned_at="2024-01-01T00:00:00+00:00",
            worktree_path=env.repo.worktrees_dir / "erk-managed-wt-01",
        )
        (env.repo.worktrees_dir / "erk-managed-wt-01").mkdir(parents=True)

        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),  # No SlotInfo entries
            assignments=(initial_slot1_assignment,),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#302", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Should show new objective
        assert "objective #99" in result.output
        # Should use slot-02 (slot-01 is assigned)
        assert "erk-managed-wt-02" in result.output

        # Verify SlotInfo was created with objective
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None

        # Should have one SlotInfo for slot-02 with the objective
        slot02_infos = [s for s in updated_state.slots if s.name == "erk-managed-wt-02"]
        assert len(slot02_infos) == 1
        assert slot02_infos[0].last_objective_issue == 99

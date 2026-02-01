# Fix: Placeholder branch creation should bypass Graphite branch manager

## Problem

When `execute_unassign` (or `init_pool`) needs to create a placeholder stub branch (e.g., `__erk-slot-46-br-stub__`), it calls `ctx.branch_manager.create_branch()`. The Graphite `create_branch` implementation checks out the parent branch (`master`) as part of Graphite tracking setup. This fails in worktrees because `master` is already checked out in the root worktree — git forbids the same branch being checked out in two worktrees simultaneously.

## Root Cause

Placeholder branches are ephemeral — they don't participate in Graphite stacks and should never be tracked. Using the full `BranchManager.create_branch` flow is both unnecessary and broken in multi-worktree contexts.

## Fix

Replace `ctx.branch_manager.create_branch()` with `ctx.git.branch.create_branch()` in both locations. The low-level `git.branch.create_branch()` runs `git branch <name> <start-point>` without any checkout or Graphite tracking.

### Files to modify

1. **`src/erk/cli/commands/slot/unassign_cmd.py`** (line 77)
   - Change: `ctx.branch_manager.create_branch(repo.root, placeholder_branch, trunk_branch)`
   - To: `ctx.git.branch.create_branch(repo.root, placeholder_branch, trunk_branch, force=False)`
   - Update the `BranchAlreadyExists` import to come from `erk_shared.gateway.git.branch_ops.types`

2. **`src/erk/cli/commands/slot/init_pool_cmd.py`** (line 108)
   - Same change: `ctx.branch_manager.create_branch(...)` → `ctx.git.branch.create_branch(...)`
   - Update imports accordingly

### Test updates

3. **`tests/unit/cli/commands/slot/test_unassign_cmd.py`**
   - Existing test `test_slot_unassign_by_slot_name` already asserts `git_ops.created_branches` contains the placeholder branch (line 82) — this assertion should still pass since `FakeGit.created_branches` tracks `git.branch.create_branch` calls.
   - Add a new regression test: `test_slot_unassign_creates_placeholder_via_git_not_branch_manager` that verifies the branch manager's `create_branch` is NOT called (i.e., no Graphite tracking for placeholder branches). This prevents future regressions.

4. **`tests/unit/cli/commands/land/test_cleanup_and_navigate.py`**
   - The `test_cleanup_and_navigate_detects_slot_by_branch_name` test exercises the full land cleanup path which calls `execute_unassign`. Existing assertions should continue to pass.

## Verification

- Run `pytest tests/unit/cli/commands/slot/test_unassign_cmd.py` — all tests pass
- Run `pytest tests/unit/cli/commands/land/test_cleanup_and_navigate.py` — all tests pass
- Run `pytest tests/unit/cli/commands/slot/` — full slot test suite passes
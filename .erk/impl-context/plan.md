# Plan: `erk br co` defaults to current worktree

## Context

Currently `erk br co <branch>` allocates a new pool slot when the branch isn't found in any existing worktree. The desired behavior: default to checking out the branch **in the current worktree** (like `git checkout`). Slot allocation should only happen with explicit `--new-slot`.

## Change Summary

**File: `src/erk/cli/commands/branch/checkout_cmd.py`**

In `_branch_checkout_impl`, restructure the three-way branch at lines 610-718 (the "no matching worktree, not `--no-slot`" path):

**Current logic:**
1. In assigned slot + no `--new-slot` → stack-in-place
2. `--for-plan` + not in slot + no `--new-slot` → checkout in current worktree
3. **else → allocate new slot** ← this changes

**New logic:**
1. In assigned slot + no `--new-slot` → stack-in-place (unchanged)
2. `--new-slot` → allocate new slot (moved from else)
3. **else → checkout in current worktree** (generalized from the for-plan-only case)

### Implementation details

1. Add helper `_find_containing_worktree(worktrees, cwd)` that finds which worktree from the list contains `ctx.cwd` (resolve paths, check if cwd is under a worktree path). Falls back to root worktree.

2. Change line 670 from `elif setup is not None and not new_slot:` to `elif new_slot:` for slot allocation, then add `else:` for checkout-in-current-worktree.

3. The new else branch:
   - Find current worktree via helper
   - `checkout_branch(current_wt.path, branch)`
   - If `setup is not None`: run `_rebase_and_track_for_plan` + `_setup_impl_for_plan`
   - Refresh worktrees, call `_perform_checkout`, return

4. Update `--new-slot` help text: "Allocate a new slot for the branch (default: checkout in current worktree)"

### Branch existence check

The existing branch existence validation (lines 587-605) already runs before the restructured block and correctly errors if the branch doesn't exist locally or on remote. No change needed there.

## Test Updates

**File: `tests/commands/branch/test_checkout_cmd.py`**

Tests that expect slot allocation as the default need updating:

| Test | Current behavior | New behavior |
|------|-----------------|--------------|
| `test_branch_checkout_reuses_inactive_slot` | Default allocates slot | Add `--new-slot` flag |
| `test_branch_checkout_creates_tracking_branch_for_remote` | Default allocates slot | Update: expect checkout in root worktree, no slot assignment message |
| `test_branch_checkout_force_unassigns_oldest` | `--force` allocates slot | Add `--new-slot` flag |
| `test_branch_checkout_stale_assignment_wrong_branch` | Default allocates slot | Add `--new-slot` flag |
| `test_branch_checkout_stale_assignment_wrong_branch_with_uncommitted_changes` | Same | Add `--new-slot` flag |

Add new test:
- `test_checkout_defaults_to_current_worktree` — verify that without `--new-slot`, a branch not in any worktree is checked out in the current worktree with no slot allocation.

## Verification

1. Run `uv run pytest tests/commands/branch/test_checkout_cmd.py`
2. Run `uv run pytest tests/commands/navigation/test_checkout.py`
3. Run type checker: `uv run ty check src/erk/cli/commands/branch/checkout_cmd.py`

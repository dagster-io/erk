---
title: Teleport Slot Awareness
read_when:
  - "modifying erk pr teleport command"
  - "understanding how teleport updates slot assignments"
  - "working with slot pool and teleport interaction"
tripwires:
  - action: "modifying teleport in-place without updating slot assignment"
    warning: "When teleporting in-place, the current worktree's slot assignment must be updated to track the new branch. Missing this breaks the slot pool's branch tracking. See `_teleport_in_place()` in teleport_cmd.py."
---

# Teleport Slot Awareness

`erk pr teleport` updates worktree slot assignments when operating in-place, matching the behavior of `erk br co` (branch checkout). This was added in PR #9225.

## Source

`src/erk/cli/commands/pr/teleport_cmd.py` — `_teleport_in_place()` function (lines ~203-214)

## When Slot Assignments Are Updated

### In-Place Teleport (`_teleport_in_place`)

After force-resetting the branch to match remote, the command updates the slot assignment.

**Source**: `src/erk/cli/commands/pr/teleport_cmd.py:203-214` — checks if in a managed slot via `load_pool_state()`, then calls `update_slot_assignment_tip()` to record the new branch name.

The slot assignment records which branch is checked out in each slot. After teleporting in-place to a new branch, the assignment must be updated so the pool knows the current branch.

### New-Slot Teleport (`_teleport_new_slot`)

When `--new-slot` is used, `ensure_branch_has_worktree()` handles slot assignment creation as part of the worktree creation process. No additional slot update is needed.

### Navigating to Existing Worktree (`_navigate_to_existing_worktree`)

When the requested branch is already checked out in another worktree, teleport navigates to it instead of overwriting. Slot assignments are not modified in this path.

## Shared Helper: `_navigate_to_existing_worktree`

This helper was extracted to share logic between `_teleport_in_place` and `_teleport_new_slot`. Both paths call it first to check if the branch is already checked out somewhere:

1. Look for existing worktree with `ctx.git.worktree.find_worktree_for_branch()`
2. If found: navigate to that worktree and exit (`SystemExit(0)`)
3. If not found: return and continue with the teleport operation

This prevents creating duplicate worktrees for the same branch.

## Relationship to `erk br co`

The slot update in teleport mirrors the behavior of `erk br co` (branch checkout). Both commands:

1. Switch branches in the current or target worktree
2. Update the slot pool's branch assignment for that worktree

This keeps the pool's state consistent regardless of which command was used to switch branches.

## Related Documentation

- [Slot Pool Architecture](../erk/slot-pool-architecture.md) — How the slot pool manages worktree assignments
- [Checkout/Teleport Split](checkout-teleport-split.md) — Conceptual difference between checkout and teleport

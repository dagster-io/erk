---
title: Four-Path Branch Cleanup in Land
read_when:
  - "modifying land_cmd.py cleanup logic"
  - "adding a new cleanup path for branch deletion"
  - "debugging branch deletion failures after landing"
tripwires:
  - action: "adding a new cleanup path in land_cmd.py without calling _ensure_branch_not_checked_out()"
    warning: "All cleanup paths must call _ensure_branch_not_checked_out() before branch deletion. Git refuses to delete branches checked out in any worktree."
    score: 6
---

# Four-Path Branch Cleanup in Land

The `erk land` command (`src/erk/cli/commands/land_cmd.py`) has five distinct cleanup paths, each handling a different worktree/slot scenario. All paths that delete branches must call `_ensure_branch_not_checked_out()` as a defensive check.

## Cleanup Paths

### 1. `_handle_no_delete` (--no-delete flag)

Preserves both the branch and slot assignment. Optionally navigates to the next branch if the current branch was the one being landed.

### 2. `_cleanup_no_worktree`

When no worktree exists for the branch (e.g., remote implementation or fork PR):

- Checks if branch exists locally
- Calls `_ensure_branch_not_checked_out()` before deletion
- Deletes the local branch

### 3. `_cleanup_slot_with_assignment`

For slot worktrees with an active assignment:

- Unassigns the slot via `execute_unassign()`
- Calls `_ensure_branch_not_checked_out()` (handles stale pool state)
- Deletes the branch

### 4. `_cleanup_slot_without_assignment`

For slot worktrees without assignment (orphaned state):

- Checks out placeholder branch in the worktree
- Calls `_ensure_branch_not_checked_out()`
- Deletes the feature branch

### 5. `_cleanup_non_slot_worktree`

For non-slot (standalone) worktrees:

- Verifies no uncommitted changes
- Checks out detached HEAD at trunk (because trunk may be checked out in root worktree)
- Calls `_ensure_branch_not_checked_out()`
- Deletes the branch
- Attempts to check out trunk if not checked out elsewhere

## The Defensive Check

`_ensure_branch_not_checked_out()` is the critical invariant: git refuses to delete a branch that is checked out in any worktree. This function verifies the branch was successfully released before attempting deletion.

**Why it matters:** Stale pool state can cause a worktree to report as removed while the branch is still checked out elsewhere. Without this check, `delete_branch()` would fail silently or raise an error.

## `CleanupContext` Dataclass

<!-- Source: src/erk/cli/commands/land_cmd.py, CleanupContext -->

All cleanup paths receive a `CleanupContext` that carries shared state. See `CleanupContext` in `src/erk/cli/commands/land_cmd.py` for all fields. The dataclass bundles all parameters needed for cleanup operations, enabling focused helper functions without parameter explosion.

## Related Topics

- [Branch Cleanup](branch-cleanup.md) - General branch cleanup patterns
- [Slot Pool Architecture](slot-pool-architecture.md) - Worktree slot mechanics
- [Placeholder Branches](placeholder-branches.md) - Placeholder branch lifecycle

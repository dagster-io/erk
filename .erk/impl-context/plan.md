# Plan: Add `slot delete` command + extract shared helpers

**Part of Objective #9272, Node 2.3 (slot-create-delete)**

## Context

We're extracting the slot system into the `erk_slots` plugin package. Node 2.4 will strip all slot awareness from the `wt` group, but first we need slot-side equivalents of the commands being removed.

**Decision: Skip `slot create-from`** — `slot checkout` already does the same thing (allocates a slot for an existing branch via `allocate_slot_for_branch`). No new command needed.

**Focus: `slot delete`** — unassign a slot + optionally delete branch/close PR/plan. The helpers for PR closing, plan closing, and branch deletion currently live in `wt/delete_cmd.py` and will be extracted to `erk_shared`.

## Implementation

### Phase 1: Extract shared helpers to `erk_shared`

**File:** `packages/erk-shared/src/erk_shared/worktree_cleanup.py` (new)

Extract these functions from `src/erk/cli/commands/wt/delete_cmd.py`:

| Function | Purpose |
|---|---|
| `close_pr_for_branch` | Close the PR associated with a branch (if open) |
| `close_plan_for_worktree` | Close the plan associated with a worktree name (if open) |
| `delete_branch_at_error_boundary` | Delete branch via BranchManager with error handling |
| `get_pr_info_for_branch` | Get PR number + state for display |
| `get_plan_info_for_worktree` | Get plan number + state for display |

These are not slot-specific — they operate on branches, PRs, and plans. Moving them to `erk_shared` gives both `wt` and `slot` a neutral import path.

**Update:** `src/erk/cli/commands/wt/delete_cmd.py` — replace inline definitions with imports from `erk_shared.worktree_cleanup`. The `_` prefix gets dropped since they're now public API.

### Phase 2: `slot delete` command

**File:** `packages/erk-slots/src/erk_slots/delete_cmd.py` (new)

Flow:
1. Resolve which slot to delete (by slot name arg, or detect from cwd)
2. Load pool state, find the assignment
3. Display planned operations
4. Confirm with user (unless `--force`)
5. Execute: unassign slot → optionally close PR → optionally close plan → optionally delete branch

**CLI interface:**
```
erk slot delete [SLOT] [-b/--branch] [-a/--all] [-f/--force] [--dry-run]
```

- `SLOT` — optional, detect from cwd if omitted (like `slot unassign`)
- `-b/--branch` — also delete the branch
- `-a/--all` — delete branch + close PR + close plan (implies `--branch`)
- `-f/--force` — skip confirmation
- `--dry-run` — show what would happen

**Imports from:**
- `erk_slots.unassign_cmd.execute_unassign` — core unassign logic
- `erk_shared.worktree_cleanup` — PR/plan/branch helpers
- `erk.cli.commands.navigation_helpers.check_pending_learn_marker` — learn marker check

**Register in:** `packages/erk-slots/src/erk_slots/group.py`

### Phase 3: Tests

**File:** `tests/unit/erk_slots/test_delete_cmd.py` (new)

Tests using fake-driven patterns:
- Slot resolution: by name, by cwd, not found
- Unassign-only (no flags): unassigns slot, no branch/PR/plan changes
- `--branch`: unassigns + deletes branch
- `--all`: unassigns + closes PR + closes plan + deletes branch
- `--force`: skips confirmation prompt
- `--dry-run`: reports but doesn't mutate

**File:** `tests/unit/erk_shared/test_worktree_cleanup.py` (new)

Tests for the extracted helpers:
- `close_pr_for_branch`: open PR → closed, already merged → no-op, no PR → no-op
- `close_plan_for_worktree`: open plan → closed, already closed → no-op
- `delete_branch_at_error_boundary`: success, user declined, git error

## Key Files

| File | Action |
|---|---|
| `packages/erk-shared/src/erk_shared/worktree_cleanup.py` | Create — extracted helpers |
| `packages/erk-slots/src/erk_slots/delete_cmd.py` | Create — slot delete command |
| `packages/erk-slots/src/erk_slots/group.py` | Modify — register slot_delete |
| `src/erk/cli/commands/wt/delete_cmd.py` | Modify — import from erk_shared |
| `tests/unit/erk_slots/test_delete_cmd.py` | Create |
| `tests/unit/erk_shared/test_worktree_cleanup.py` | Create |

## Verification

1. `erk slot delete <slot-name>` — unassigns only
2. `erk slot delete <slot-name> -b` — unassigns + deletes branch
3. `erk slot delete <slot-name> -a` — unassigns + closes PR + closes plan + deletes branch
4. `erk slot --help` — shows `delete` in command list
5. `pytest tests/unit/erk_slots/test_delete_cmd.py tests/unit/erk_shared/test_worktree_cleanup.py`
6. `make fast-ci`

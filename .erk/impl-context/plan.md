# Plan: Error when `--new-slot` is used but branch already exists in a worktree

## Context

`erk br co --new-slot --for-plan 8254` silently ignores `--new-slot` when the target branch already exists in a worktree. The command finds the branch in erk-slot-51 and jumps to it, printing "Using existing branch" with no indication that `--new-slot` was disregarded. This violates the user's explicit intent to create a new slot.

## Root Cause

In `checkout_cmd.py`, `find_worktrees_containing_branch()` runs at line ~453 **before** the `--new-slot` check at line ~513. When a match is found (`len(matching_worktrees) == 1` at line 580), the code jumps straight to the existing worktree. The `--new-slot` flag is only consulted inside the `len(matching_worktrees) == 0` branch (Case 1).

## Fix

Add a guard in the `len(matching_worktrees) == 1` branch (line 580) that checks if `new_slot` is True. If so, raise a `click.ClickException` with a clear message identifying which worktree already has the branch.

### File: `src/erk/cli/commands/branch/checkout_cmd.py`

**At line 580**, before the existing single-match logic, insert:

```python
if len(matching_worktrees) == 1:
    # --new-slot was requested but the branch already exists in a worktree
    if new_slot:
        target_worktree = matching_worktrees[0]
        raise click.ClickException(
            f"Branch '{branch}' is already checked out in {target_worktree.path.name}. "
            f"Cannot create a new slot for an existing branch."
        )
    # ... rest of existing logic
```

Also add the same guard in the `len(matching_worktrees) > 1` branch (line 600) for completeness — though unlikely in practice, `--new-slot` should error there too.

## Verification

1. Run `erk br co --new-slot --for-plan <plan-with-existing-branch>` — should error with clear message
2. Run `erk br co --for-plan <plan-with-existing-branch>` (no `--new-slot`) — should still jump to existing worktree as before
3. Run `erk br co --new-slot --for-plan <plan-with-no-branch>` — should allocate a new slot as before
4. Run existing tests: `pytest tests/ -k checkout`

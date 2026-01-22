# Fix: Stale pool.json State Handling in `erk br co`

## Problem

When pool.json says a branch is assigned to a slot, but the worktree has a different branch checked out:

1. `allocate_slot_for_branch()` trusts pool.json and returns `already_assigned=True` without verifying worktree state
2. The `else` branch in checkout_cmd.py shows "multiple worktrees" error even when there are zero matches

## Root Cause

pool.json can become stale when:
- A slot is reused for a different branch manually
- External git operations change the checked-out branch
- Previous erk operations failed mid-way

## Implementation

### 1. Fix `allocate_slot_for_branch()` in `src/erk/cli/commands/slot/common.py`

At lines 384-392, before returning `already_assigned=True`, verify the worktree:

```python
existing = find_branch_assignment(state, branch_name)
if existing is not None:
    # First check if worktree exists
    if not existing.worktree_path.exists():
        # Remove stale assignment, fall through to normal allocation
        # ... update state, save pool.json, log warning
    else:
        # Verify worktree has correct branch
        actual_branch = ctx.git.get_current_branch(existing.worktree_path)
        if actual_branch == branch_name:
            return SlotAllocationResult(...)  # fast path

        # Mismatch - check for uncommitted changes before fixing
        if ctx.git.has_uncommitted_changes(existing.worktree_path):
            user_output(f"Warning: {existing.slot_name} has uncommitted changes...")
            raise SystemExit(1)

        # Fix by checking out correct branch
        ctx.git.checkout_branch(existing.worktree_path, branch_name)
        return SlotAllocationResult(...)
```

### 2. Fix error message in `src/erk/cli/commands/branch/checkout_cmd.py`

At lines 385-393, distinguish zero vs multiple:

```python
else:
    if len(directly_checked_out) == 0:
        user_output(
            f"Error: Internal state mismatch. Branch '{branch}' was allocated "
            f"but no worktree has it checked out.\n"
            f"This may indicate corrupted pool state."
        )
        raise SystemExit(1)
    else:
        # Actual multiple worktrees case
        user_output(f"Branch '{branch}' exists in multiple worktrees:")
        ...
```

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/slot/common.py` | Add worktree verification logic |
| `src/erk/cli/commands/branch/checkout_cmd.py` | Improve error message |
| `tests/unit/cli/commands/slot/test_common.py` | Add verification tests |
| `tests/commands/branch/test_checkout_cmd.py` | Add error message tests |

## Edge Cases

- **Uncommitted changes**: Fail gracefully, don't auto-checkout
- **Missing worktree**: Remove stale assignment from pool.json, proceed with normal allocation
- **Detached HEAD**: Treat as mismatch, fix with checkout

## Verification

1. Run `make fast-ci` to ensure tests pass
2. Manual test: Create stale state by:
   - `erk br co some-branch` (assigns to slot)
   - Manually `cd` to slot and `git checkout different-branch`
   - Run `erk br co some-branch` - should now fix the worktree instead of erroring

## Related Skills

- `dignified-python`: LBYL patterns, no try/except for control flow
- `fake-driven-testing`: Test patterns with FakeGit
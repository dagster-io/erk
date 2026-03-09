# Fix Slot Reuse in erk up/down Navigation

## Context

When running `erk up` or `erk down` and the target branch isn't checked out in any existing worktree, the navigation commands call `ensure_worktree_for_branch()` which creates a **new, unmanaged worktree** (named after the branch, outside the slot pool). This is wrong — it should use `allocate_slot_for_branch()` to assign the branch to a pool slot, matching how `erk branch checkout` and `erk slot assign` work.

The user's scenario: running `erk up` from a slot shows "Branch 'X' not checked out, creating worktree..." and creates a new worktree directory named after the branch instead of reusing an available slot.

## Root Cause

In `src/erk/cli/commands/navigation_helpers.py`:
- `resolve_up_navigation()` (line 547) calls `ensure_worktree_for_branch()` when no worktree exists
- `resolve_down_navigation()` (line 605) calls `ensure_worktree_for_branch()` when no worktree exists

`ensure_worktree_for_branch()` (from `wt/create_cmd.py`) creates an unmanaged worktree via `add_worktree()` — it bypasses the slot pool entirely.

The correct approach is to use `allocate_slot_for_branch()` (from `slot/common.py`), the same function used by `erk branch checkout` and `erk slot assign`.

## Changes

### 1. Modify `src/erk/cli/commands/navigation_helpers.py`

**Change imports** (line 17):

Replace:
```python
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
```

With:
```python
from erk.cli.commands.checkout_helpers import ensure_branch_has_worktree
```

**Modify `resolve_up_navigation()`** (lines 546-548):

Replace:
```python
    # No worktree found - auto-create
    _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, target_branch)
    return target_branch, was_created
```

With:
```python
    # No worktree found - allocate a slot
    _worktree_path, already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=target_branch, no_slot=False, force=False
    )
    return target_branch, not already_existed
```

Note: `ensure_branch_has_worktree()` returns `(path, already_existed)` where `already_existed=True` means it was already there and `already_existed=False` means a slot was allocated. The navigation function returns `(branch, was_created)` so we invert the boolean.

**Modify `resolve_down_navigation()`** (lines 604-606):

Replace:
```python
        # No worktree found - auto-create
        _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
        return parent_branch, was_created
```

With:
```python
        # No worktree found - allocate a slot
        _worktree_path, already_existed = ensure_branch_has_worktree(
            ctx, repo, branch_name=parent_branch, no_slot=False, force=False
        )
        return parent_branch, not already_existed
```

**Update the "Created worktree" message in `execute_stack_navigation()`** (lines 780-785):

Replace:
```python
    # Show creation message if worktree was just created
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree for {click.style(target_name, fg='yellow')} and moved to it"
        )
```

With:
```python
    # Show creation message if slot was just assigned
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Assigned slot for {click.style(target_name, fg='yellow')} and moved to it"
        )
```

### 2. Update `src/erk/cli/commands/checkout_helpers.py` — No changes needed

`ensure_branch_has_worktree()` already exists (lines 219-277) with exactly the right behavior:
1. Checks if branch already has a worktree (returns it)
2. If not, calls `allocate_slot_for_branch()` with `reuse_inactive_slots=True, cleanup_artifacts=True`
3. Writes activation script
4. Shows "Assigned {branch} to {slot}" message

This function is already imported and used in branch checkout. Navigation just needs to call it.

### 3. Update tests

#### `tests/commands/navigation/test_up.py`

**Modify `test_up_child_has_no_worktree()`** (line 130):

This test currently uses `erk_isolated_fs_env` and checks `git_ops.added_worktrees` to verify a new worktree was created. With slot allocation, the behavior changes — the branch is assigned to a pool slot via `allocate_slot_for_branch()` which internally calls `checkout_branch()` on an inactive slot or creates a new slot worktree.

The test needs to:
1. Set up pool state (or let the default empty pool be used)
2. Verify the command succeeds (exit code 0)
3. Verify pool state was updated (branch was assigned to a slot)

Replace the test body to:
- Use `erk_isolated_fs_env` (still needed for filesystem operations)
- Pre-create a pool with an idle slot (to test the reuse path) OR let the system create a new slot
- Assert that `pool.json` contains an assignment for `feature-2` after the command runs
- Assert the script points to a slot directory path (e.g., `erk-slot-01`)

**Add `test_up_child_no_worktree_assigns_slot()`**:

A new test that explicitly verifies:
1. Set up pool state with one assigned slot and one available slot
2. Run `erk up` where the child branch has no worktree
3. Verify the child branch gets assigned to the available slot
4. Verify the script points to the correct slot directory
5. Verify pool.json is updated

#### `tests/commands/navigation/test_down.py`

**Modify `test_down_parent_has_no_worktree()`** (line 155):

Same pattern as the up test — verify slot assignment instead of raw worktree creation.

**Add `test_down_parent_no_worktree_assigns_slot()`**:

Mirror of the up test for the down direction.

### 4. Also fix `src/erk/cli/commands/land_cmd.py` (line 1233)

`land_cmd.py` also calls `ensure_worktree_for_branch()` when auto-creating a worktree for a child branch after landing. This should also use slot allocation:

Replace (line 1233-1235):
```python
            target_path, _ = ensure_worktree_for_branch(
                ctx, post_deletion_repo, target_child_branch
            )
```

With:
```python
            target_path, _ = ensure_branch_has_worktree(
                ctx, post_deletion_repo, branch_name=target_child_branch, no_slot=False, force=False
            )
```

Update the import at the top of the file correspondingly:
- Remove: `from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch`
- Add: `from erk.cli.commands.checkout_helpers import ensure_branch_has_worktree`

## Files Changing

| File | Change |
|------|--------|
| `src/erk/cli/commands/navigation_helpers.py` | Replace `ensure_worktree_for_branch` with `ensure_branch_has_worktree`, update message |
| `src/erk/cli/commands/land_cmd.py` | Replace `ensure_worktree_for_branch` with `ensure_branch_has_worktree` |
| `tests/commands/navigation/test_up.py` | Update `test_up_child_has_no_worktree`, add slot assignment test |
| `tests/commands/navigation/test_down.py` | Update `test_down_parent_has_no_worktree`, add slot assignment test |

## Files NOT Changing

- `src/erk/cli/commands/wt/create_cmd.py` — `ensure_worktree_for_branch()` stays; it's still used by `branch/checkout_cmd.py` with `no_slot=True` path
- `src/erk/cli/commands/checkout_helpers.py` — Already has the right function, no modifications needed
- `src/erk/cli/commands/slot/common.py` — Slot allocation logic is unchanged
- `src/erk/cli/commands/branch/checkout_cmd.py` — Already uses the correct pattern

## Implementation Notes

- `ensure_branch_has_worktree()` with `no_slot=False` calls `allocate_slot_for_branch()` which handles: existing assignment check, inactive slot reuse, new slot creation, and pool-full eviction
- The `force=False` parameter means if the pool is full and no slots can be evicted, the user gets an interactive prompt (or error in non-TTY). This is reasonable for navigation — the user should know their pool is full
- `ensure_branch_has_worktree()` already calls `ensure_worktree_activate_script()` so the activation script will be written correctly
- The `ensure_branch_has_worktree()` function prints its own "Assigned X to Y" message, so the orchestrator's "Created worktree" message can be simplified or kept as a secondary confirmation

## Verification

1. Run `make test` — all existing navigation tests should pass (after test updates)
2. Run `make fast-ci` — full CI validation
3. Manual verification scenario:
   - Create a stack: `main -> feature-1 -> feature-2`
   - Only have `feature-1` in a slot
   - Run `erk up` from `feature-1` — should assign `feature-2` to a slot, not create an unmanaged worktree
   - Run `erk down` from `feature-2` back to `feature-1` — should find existing slot
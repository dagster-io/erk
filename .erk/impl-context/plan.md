# Rebase Stub Branch onto Master After Landing

## Context

After `erk land` completes in a pool slot worktree, the slot is unassigned and the placeholder/stub branch (`__erk-slot-NN-br-stub__`) is checked out. However, the stub branch may point to a stale commit from when it was last created or used, leaving the slot worktree far behind master.

The user expects the stub branch to be current with master so the next branch created in that slot starts from an up-to-date state. Currently, users must manually rebase the stub branch after landing.

### Why This Matters

When `execute_unassign()` checks out the placeholder branch (line 76-85 of `src/erk/cli/commands/slot/unassign_cmd.py`):

- If the placeholder branch **doesn't exist**, it's created from trunk (current) — this is fine
- If the placeholder branch **already exists** (the common case after pool initialization), it's checked out as-is — **this leaves a stale worktree**

The stub branch was created at pool init time (or last unassign) and has never been updated since. After landing, the user is left in a slot with files from an arbitrarily old commit.

## Changes

### File: `src/erk/cli/commands/slot/unassign_cmd.py`

**Function: `execute_unassign()`** — Add a step to force-update the placeholder branch to trunk before checkout.

Current flow (lines 76-85):
```python
if placeholder_branch not in local_branches:
    create_result = ctx.git.branch.create_branch(
        repo.root, placeholder_branch, trunk_branch, force=False
    )
    if isinstance(create_result, BranchAlreadyExists):
        user_output(f"Error: {create_result.message}")
        raise SystemExit(1) from None

# Checkout placeholder branch in the worktree
ctx.branch_manager.checkout_branch(assignment.worktree_path, placeholder_branch)
```

New flow:
```python
if placeholder_branch not in local_branches:
    create_result = ctx.git.branch.create_branch(
        repo.root, placeholder_branch, trunk_branch, force=False
    )
    if isinstance(create_result, BranchAlreadyExists):
        user_output(f"Error: {create_result.message}")
        raise SystemExit(1) from None
else:
    # Force-update existing placeholder to trunk so the slot worktree
    # starts fresh after unassignment (e.g., after erk land)
    ctx.git.branch.create_branch(
        repo.root, placeholder_branch, trunk_branch, force=True
    )

# Checkout placeholder branch in the worktree
ctx.branch_manager.checkout_branch(assignment.worktree_path, placeholder_branch)
```

**Why `create_branch(force=True)` is safe here**: The placeholder branch is not checked out at this point — the feature branch being unassigned/landed is still checked out. `git branch -f <name> <start_point>` works on branches that aren't currently checked out. After the force-update, the subsequent `checkout_branch` switches to the now-current placeholder.

**Why change `execute_unassign()` instead of `land_cmd.py`**: The `execute_unassign()` function is the single place that transitions a slot from assigned→unassigned. Fixing it here benefits both `erk land` (via `_cleanup_slot_with_assignment`) and `erk slot unassign` (the direct CLI command).

### File: `src/erk/cli/commands/land_cmd.py`

**Function: `_cleanup_slot_without_assignment()`** (lines 351-373) — Add the same force-update before checkout.

This function handles the case where a branch was checked out in a slot without using erk's assignment system. It checks out the placeholder directly (not via `execute_unassign`), so it needs the same fix.

Current flow (lines 361-366):
```python
# Checkout placeholder branch before deleting the feature branch
# worktree_path is guaranteed non-None since we're in a slot worktree
assert cleanup.worktree_path is not None
placeholder = get_placeholder_branch_name(slot_name)
if placeholder is not None:
    cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, placeholder)
```

New flow:
```python
# Checkout placeholder branch before deleting the feature branch
# worktree_path is guaranteed non-None since we're in a slot worktree
assert cleanup.worktree_path is not None
placeholder = get_placeholder_branch_name(slot_name)
if placeholder is not None:
    # Force-update placeholder to trunk so the slot starts fresh
    trunk = cleanup.ctx.git.branch.detect_trunk_branch(cleanup.main_repo_root)
    cleanup.ctx.git.branch.create_branch(
        cleanup.main_repo_root, placeholder, trunk, force=True
    )
    cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, placeholder)
```

### File: `tests/unit/cli/commands/slot/test_unassign_cmd.py`

Add a test verifying that existing placeholder branches are force-updated to trunk during unassign.

**Test: `test_execute_unassign_updates_existing_placeholder_to_trunk`**

Setup:
- Create a slot with an assignment (feature-branch checked out)
- Pre-create the placeholder branch in local_branches (simulating it already exists from pool init)
- Call `execute_unassign()`

Assertions:
- Verify `create_branch` was called with `force=True` for the placeholder branch with trunk as start_point
- Verify placeholder was checked out in the worktree
- Verify assignment was removed from pool state

**Test: `test_execute_unassign_creates_new_placeholder_when_missing`** (existing behavior, ensure no regression)

Verify that when placeholder doesn't exist, it's still created with `force=False` as before.

### File: `tests/unit/cli/commands/land/test_cleanup_and_navigate.py`

Add a test for the `_cleanup_slot_without_assignment` path:

**Test: `test_cleanup_slot_without_assignment_updates_stub_to_trunk`**

Setup:
- Slot worktree with feature branch checked out
- Placeholder branch exists but is stale
- Call `_cleanup_and_navigate` with `SLOT_UNASSIGNED` cleanup type

Assertions:
- Verify `create_branch(force=True)` was called for the placeholder to reset it to trunk
- Verify placeholder was checked out
- Verify feature branch was deleted

## Files NOT Changing

- **`src/erk/cli/commands/slot/common.py`** — No changes needed to `get_placeholder_branch_name()` or other utilities
- **`src/erk/cli/commands/land_pipeline.py`** — The pipeline orchestration doesn't need changes; cleanup is in `land_cmd.py`
- **`src/erk/cli/commands/slot/init_pool_cmd.py`** — Pool initialization creates stubs from trunk already; no fix needed there
- **`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/`** — The `create_branch(force=True)` API already exists and does exactly what we need
- **`docs/learned/erk/placeholder-branches.md`** — Could optionally be updated to mention the force-update behavior, but not required

## Implementation Details

### Key Design Decision: Force-Update vs Delete+Recreate

Two approaches were considered:

1. **Force-update** (`create_branch(force=True)`): Moves existing branch to trunk. Single git command (`git branch -f`).
2. **Delete+Recreate** (`delete_branch` then `create_branch`): Two git commands, more explicit.

Force-update is preferred because:
- Single atomic operation
- The `create_branch(force=True)` API already exists and is well-tested
- Simpler code path
- Already used in production (see `pr/checkout_cmd.py:116`)

### Edge Cases

1. **Placeholder branch checked out in another worktree**: Cannot happen. Each slot has a unique placeholder (`__erk-slot-01-br-stub__` vs `__erk-slot-02-br-stub__`), and only one slot can use each placeholder.

2. **Trunk branch doesn't exist locally**: `detect_trunk_branch()` falls back to checking remote HEAD, then 'main', then 'master'. This is robust.

3. **Dry-run mode**: The `execute_unassign` function already guards pool state saves with `ctx.dry_run`. The `create_branch(force=True)` call should also be guarded. Check if the dry-run decorator on the git gateway handles this automatically — if `RealGitBranchOps` has a `DryRunGitBranchOps` wrapper, it will be handled transparently. Verify during implementation.

4. **Force-update of a branch that doesn't exist**: The `else` branch only executes when `placeholder_branch in local_branches`, so this cannot happen.

## Verification

1. **Run existing tests**: `pytest tests/unit/cli/commands/land/ tests/unit/cli/commands/slot/` — all existing tests should still pass
2. **Run new tests**: Verify the new test cases pass
3. **Type check**: Run `ty` to verify type correctness
4. **Manual verification scenario**:
   - `erk slot init-pool` (creates stubs at current master)
   - `erk branch checkout some-feature` (assigns slot, checks out feature)
   - Make some commits on master (stubs are now stale)
   - `erk land` (should leave stub at current master, not the old commit)
   - Verify: `git log -1` in the slot should show master's HEAD, not the old commit
# Plan: Extract Slot Allocation Logic to Common Module

## Problem

The slot allocation pattern is duplicated across 5 commands (~70-110 lines each):

1. `pr/checkout_cmd.py` - `_allocate_slot_for_branch()`
2. `branch/create_cmd.py` - inline in `branch_create()`
3. `plan/start_cmd.py` - inline in `plan_start()`
4. `implement.py` - `_create_worktree_with_plan_content()`
5. `slot/assign_cmd.py` - inline in `slot_assign()`

The same algorithm appears everywhere:
1. Load pool state (or create default)
2. Check if branch already assigned → return early
3. Try `find_inactive_slot()` → if found, reuse worktree
4. Try `find_next_available_slot()` → if None, pool is full
5. Handle pool-full with `handle_pool_full_interactive()`
6. Create worktree or checkout branch
7. Create and save new `SlotAssignment`

## Solution

Extract a unified `allocate_slot_for_branch()` function to `src/erk/cli/commands/slot/common.py`.

### New Data Structure

```python
@dataclass(frozen=True)
class SlotAllocationResult:
    """Result of allocating a slot for a branch."""
    slot_name: str
    worktree_path: Path
    already_assigned: bool  # True if branch was already in a slot
```

### New Function Signature

```python
def allocate_slot_for_branch(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    *,
    force: bool,
    reuse_inactive_slots: bool = True,
    cleanup_artifacts: bool = True,
) -> SlotAllocationResult:
    """Allocate a pool slot for a branch and setup the worktree.

    This is the unified slot allocation algorithm used by all commands
    that need to assign branches to pool slots.

    The branch MUST already exist before calling this function.

    Args:
        ctx: Erk context (uses ctx.time.now() for testable timestamps)
        repo: Repository context with pool_json_path and worktrees_dir
        branch_name: Name of existing branch to assign
        force: Auto-unassign oldest if pool is full (no interactive prompt)
        reuse_inactive_slots: Try to reuse unassigned worktrees first (default True)
        cleanup_artifacts: Remove .impl/ and .erk/scratch/ on worktree reuse

    Returns:
        SlotAllocationResult with slot info

    Raises:
        SystemExit(1): If pool is full and user declined to unassign
    """
```

## Implementation Steps

### Step 1: Add `SlotAllocationResult` dataclass to `common.py`

Add the frozen dataclass near the top of the file with the other data structures.

### Step 2: Implement `allocate_slot_for_branch()` in `common.py`

Extract the common algorithm, using:
- `ctx.time.now()` for testable timestamps (not `datetime.now(UTC)`)
- Configurable `reuse_inactive_slots` parameter
- Configurable `cleanup_artifacts` parameter

### Step 3: Refactor `pr/checkout_cmd.py`

Replace `_allocate_slot_for_branch()` with call to common function:
```python
result = allocate_slot_for_branch(ctx, repo, branch_name, force=force)
if result.already_assigned:
    return result.worktree_path
return result.worktree_path
```

### Step 4: Refactor `branch/create_cmd.py`

Replace inline allocation logic (~60 lines) with:
```python
# Branch is created before this point
result = allocate_slot_for_branch(ctx, repo, branch_name, force=force)
user_output(click.style(f"✓ Assigned {branch_name} to {result.slot_name}", fg="green"))
```

### Step 5: Refactor `slot/assign_cmd.py`

Replace inline allocation logic (~50 lines) with:
```python
result = allocate_slot_for_branch(
    ctx, repo, branch_name,
    force=force,
    reuse_inactive_slots=True,  # Fix: was missing this
)
if result.already_assigned:
    user_output(f"Error: Branch '{branch_name}' already assigned to {result.slot_name}")
    raise SystemExit(1)
```

Note: This also fixes a bug where `slot assign` wasn't trying inactive slots.

### Step 6: Refactor `plan/start_cmd.py`

Replace inline allocation logic (~70 lines), keeping command-specific logic:
- Branch creation (before allocation)
- Dry-run mode check
- Post-worktree setup
- Claude launch

### Step 7: Refactor `implement.py`

Replace inline allocation logic in `_create_worktree_with_plan_content()` (~75 lines), keeping:
- Uncommitted changes check
- Objective tracking
- `.impl/` folder creation
- Dry-run mode

## Files to Modify

1. `src/erk/cli/commands/slot/common.py` - Add `SlotAllocationResult` and `allocate_slot_for_branch()`
2. `src/erk/cli/commands/pr/checkout_cmd.py` - Remove `_allocate_slot_for_branch()`, use common
3. `src/erk/cli/commands/branch/create_cmd.py` - Remove inline logic, use common
4. `src/erk/cli/commands/slot/assign_cmd.py` - Remove inline logic, use common (+ bug fix)
5. `src/erk/cli/commands/plan/start_cmd.py` - Remove inline logic, use common
6. `src/erk/cli/commands/implement.py` - Remove inline logic, use common

## Testing

Existing tests should continue to pass since behavior is preserved. The bug fix in `slot assign` (adding inactive slot reuse) may need test verification.

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Manual test: `erk pr checkout`, `erk branch create`, `erk slot assign`, `erk plan start`, `erk implement` all work correctly
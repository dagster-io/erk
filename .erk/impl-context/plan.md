# Plan: Add `--new-slot` flag to `erk br create`

## Context

When running `erk br create` from inside an assigned slot, it automatically stacks in place — updating the existing slot assignment to point to the new branch. There's no way to override this and force allocation of a separate slot. The `--new-slot` flag gives users explicit control when they want the new branch in its own slot.

## Changes

### 1. Add `--new-slot` Click option

**File:** `src/erk/cli/commands/branch/create_cmd.py`

Add after `--no-slot` option (line 43):

```python
@click.option("--new-slot", is_flag=True, help="Force allocation of a new slot instead of stacking in place")
```

Add `new_slot: bool` parameter to the function signature.

### 2. Add mutual exclusivity validation

**File:** `src/erk/cli/commands/branch/create_cmd.py`

In the validation block (after line 120), add:

```python
if new_slot and no_slot:
    user_output("Error: --new-slot and --no-slot cannot be used together.")
    raise SystemExit(1) from None
```

### 3. Skip stack-in-place detection when `--new-slot`

**File:** `src/erk/cli/commands/branch/create_cmd.py`

Change the condition on line 214 from:

```python
if state is not None:
```

to:

```python
if state is not None and not new_slot:
```

This causes `current_assignment` to remain `None`, so execution falls through to `allocate_slot_for_branch()`.

### 4. Add test

**File:** `tests/unit/cli/commands/branch/test_create_cmd.py`

Add `test_branch_create_new_slot_forces_allocation_from_assigned_slot` following the pattern of `test_branch_create_stacks_in_place_from_assigned_slot` (line 836). The test should:

- Pre-create pool state with cwd assigned to `erk-slot-01`
- Invoke `["br", "create", "--new-slot", "new-branch"]`
- Assert output says "Assigned" not "Stacked"
- Assert `len(state.assignments) == 2` (original + new)
- Assert no worktree_path collision between the two assignments

## Verification

- Run `uv run pytest tests/unit/cli/commands/branch/test_create_cmd.py` — all tests pass
- Run `uv run ruff check src/erk/cli/commands/branch/create_cmd.py` — no lint errors
- Run `uv run ty check src/erk/cli/commands/branch/create_cmd.py` — no type errors

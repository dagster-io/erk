# Plan: Simplify `erk slot checkout` UX — Remove `--new-slot`, Add `erk slot goto`

## Context

The user ran the "Next steps" commands output by plan-save and hit two problems:
1. `erk br co --new-slot --for-plan 9286` failed because `--new-slot` doesn't exist on `erk br co` (already partially fixed on this branch by changing to `erk slot co`, but `--new-slot` is still referenced)
2. The `--new-slot` flag on `erk slot checkout` is redundant — checkout should always allocate a new slot

The goal is to simplify the command model:
- **`erk slot checkout BRANCH`** — always allocates a new slot (no stack-in-place)
- **`erk slot goto SLOT`** — navigate to an existing slot by name/number

## Changes

### 1. Remove `--new-slot` and stack-in-place from `erk slot checkout`

**File:** `packages/erk-slots/src/erk_slots/checkout_cmd.py`

- Remove the `--new-slot` Click option (lines 333-336) and `new_slot` parameter from `slot_checkout` and `_slot_checkout_impl`
- Remove the entire stack-in-place block (lines 599-644) — the `if not new_slot:` guard and its `update_slot_assignment_tip()` call
- Remove `update_slot_assignment_tip` from the imports (line 52) — still used by `create_cmd.py` and `teleport_cmd.py` so keep it in `common.py`
- Remove `find_current_slot_assignment` import (line 51) if no longer used
- Update docstring and examples to remove `--new-slot` references

After this change, when a branch isn't found in any worktree and isn't trunk, the code falls straight through to `allocate_slot_for_branch()`.

### 2. Add `erk slot goto` command

**New file:** `packages/erk-slots/src/erk_slots/goto_cmd.py`

Command: `erk slot goto SLOT [--script]`

- Takes a SLOT argument — accepts either full slot name (`erk-slot-03`) or just the number (`3`)
- Looks up the slot in pool state (`load_pool_state`)
- Finds the assignment for that slot
- Navigates to the slot's worktree using `navigate_to_worktree()` from `checkout_helpers.py`
- Supports `--script` option for `source "$(erk slot goto 3 --script)"` pattern
- Errors if slot not found or not assigned

Reuse existing utilities:
- `load_pool_state()` from `erk.core.worktree_pool`
- `navigate_to_worktree()` from `erk.cli.commands.checkout_helpers`
- `script_error_handler()` from `erk.cli.commands.checkout_helpers`
- `script_option` from `erk.cli.help_formatter`
- `generate_slot_name()` from `erk_slots.common` (to convert number to slot name)

### 3. Register `erk slot goto` in the slot group

**File:** `packages/erk-slots/src/erk_slots/__init__.py`

- Import `slot_goto` from `goto_cmd`
- Add `slot_group.add_command(slot_goto)`

### 4. Fix `next_steps.py` — remove `--new-slot` references

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

- Remove `checkout_new_slot` property entirely
- Remove `--new-slot` from `implement_new_wt` and `implement_new_wt_dangerous` (just drop the flag, keep `--script`)
- Simplify `format_pr_next_steps_plain()`:
  - Checkout section: single line (no "In current wt" / "In new wt" for checkout since there's no `--new-slot` distinction)
  - Implement section: keep "In current wt" / "In new wt" (the distinction is about `--script`, still valid)

### 5. Update tests

**File:** `packages/erk-slots/tests/unit/test_checkout_cmd.py`
- Remove `test_slot_checkout_stack_in_place` test (line 103)
- Remove `test_slot_checkout_new_slot_forces_allocation` test (line 155)
- `test_slot_checkout_allocates_new_slot` stays (this is now the default behavior)

**New file:** `packages/erk-slots/tests/unit/test_goto_cmd.py`
- Test: goto by full slot name navigates to worktree
- Test: goto by slot number navigates to worktree
- Test: goto non-existent slot errors
- Test: goto unassigned slot errors
- Test: goto with `--script` outputs activation script

**File:** `packages/erk-shared/tests/unit/output/test_next_steps.py`
- Remove `test_plan_next_steps_checkout_new_slot` test
- Update `test_plan_next_steps_implement_new_wt` — remove `--new-slot` from expected string
- Update `test_plan_next_steps_implement_new_wt_dangerous` — same
- Update `test_format_pr_next_steps_plain_contains_checkout_new_slot` — remove or update
- Update other assertions that reference `--new-slot`

## Verification

1. Run unit tests: `make fast-ci` (via devrun agent)
2. Run `erk slot checkout -h` — confirm no `--new-slot` in help
3. Run `erk slot goto -h` — confirm command exists with SLOT argument and `--script` option
4. Manual: `erk slot checkout <branch>` always allocates a new slot even when inside a slot
5. Manual: `erk slot goto <slot-name>` navigates to the slot's worktree

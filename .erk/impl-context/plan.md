# Remove `--new-slot` from `erk slot teleport`

## Context

`--new-slot` doesn't make sense for teleport, just as it doesn't make sense for `erk slot checkout`. Both commands target a specific existing PR/branch, so slot allocation should happen automatically. `erk slot checkout` already does this — it calls `allocate_slot_for_branch` which finds the existing assignment or creates one. Teleport should work the same way.

Currently teleport has two separate code paths: in-place (default) and new-slot. The unified behavior should be: always ensure the branch has a slot (via `allocate_slot_for_branch`), navigate to it, and force-reset to match remote.

## Changes

### 1. Simplify `teleport_cmd.py`

**File**: `packages/erk-slots/src/erk_slots/teleport_cmd.py`

- Remove `--new-slot` Click option
- Remove `new_slot` parameter from `slot_teleport()`
- Remove `is_new_slot` field from `TeleportPlan`
- Delete `_teleport_new_slot()` and `_execute_new_slot_teleport()`
- Rewrite `_teleport_in_place()` → single `_build_teleport_plan()` that:
  - Checks if branch already in a worktree; if not, allocates a slot via `ensure_branch_has_worktree()`
  - Fetches remote, computes divergence, gathers state
- Rewrite `_execute_in_place_teleport()` → single `_execute_teleport()` that:
  - If branch was NOT already in a worktree, navigates to the newly allocated slot
  - Confirms overwrite if there's local divergence (unless `--force`)
  - Force-resets branch to match remote
  - Updates slot assignment
  - Registers with Graphite
  - Displays result
- Update `_navigate_to_existing_worktree()` to force-reset the branch at the existing worktree instead of just navigating (this is teleport, not checkout)
- Update `_display_dry_run_report()` to remove `is_new_slot` references

### 2. Remove TUI duplicate entry

**File**: `src/erk/tui/commands/registry.py`

- Remove `_display_copy_teleport_new_slot()` function (line 117-119)
- Remove the `copy_teleport_new_slot` `CommandDefinition` entry (lines 456-465)
- Update `_display_cmux_teleport()` (line 127-129): remove `--new-slot` from the command string
- Keep `copy_teleport` and `_display_copy_teleport` as-is (they already don't include `--new-slot`)

### 3. Update cmux checkout workspace script

**File**: `src/erk/cli/commands/exec/scripts/cmux_checkout_workspace.py`

- Line 118: Remove `--new-slot` from the teleport command string
- Line 13 (docstring): Remove `--new-slot` reference

### 4. Update cmux SKILL.md

**File**: `.claude/skills/cmux/SKILL.md`

- Lines 156, 159, 211: Remove `--new-slot` from teleport command examples

### 5. Update documentation

**File**: `docs/learned/cli/checkout-teleport-split.md`

- Line 38: Remove `[--new-slot]` from usage syntax
- Line 62: Remove `--new-slot` from teleport description
- Line 74: Remove `--new-slot` from table entry

### 6. Update tests

**File**: `tests/commands/pr/test_teleport.py`

- `test_teleport_new_slot_existing_worktree_navigates` (line 300): Remove `--new-slot` from invocation — this test should still pass since teleport always navigates to existing worktrees
- `test_teleport_new_slot_existing_worktree_script_mode` (line 327): Remove `--new-slot`
- `test_teleport_new_slot_script_mode_with_sync_includes_gt_submit` (line 359): Remove `--new-slot`, update test name
- `test_teleport_new_slot_script_mode_without_sync_omits_gt_submit` (line 390): Remove `--new-slot`, update test name
- `test_teleport_dry_run_new_slot` (line 564): Remove `--new-slot`, update assertion from "Would create new worktree slot" to something appropriate for the unified flow

**File**: `tests/tui/commands/test_execute_command.py`

- Line 131-136: Remove `--new-slot` from test name and expected command

**File**: `tests/tui/commands/test_registry.py`

- Lines 340-344: Remove test for `copy_teleport_new_slot` display
- Lines 360-362: Update expected command string for cmux_teleport (remove `--new-slot`)
- Line 939: Update expected command string (remove `--new-slot`)

## Verification

1. Run teleport tests: `uv run pytest tests/commands/pr/test_teleport.py`
2. Run TUI tests: `uv run pytest tests/tui/`
3. Run type checker: `uv run ty check src/erk/tui/commands/registry.py packages/erk-slots/src/erk_slots/teleport_cmd.py`
4. Manual: `erk slot teleport <PR> --script --sync` should allocate a slot and teleport without needing `--new-slot`

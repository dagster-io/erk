# Plan: Move navigation into erk_slots (Node 2.1, Objective #9272)

## Context

Part of Objective #9272 (Extract Slot System into Plugin Package), Node 2.1.

The `erk up` and `erk down` commands navigate the worktree stack with slot-aware allocation. They belong in `erk_slots` since they're tightly coupled to the slot system. This PR moves them to `erk slot up` / `erk slot down` and splits `navigation_helpers.py` to separate navigation-specific logic from shared utilities.

## Approach

### 1. Create `erk_slots/navigation.py` — extract navigation-specific functions

Move these functions from `src/erk/cli/commands/navigation_helpers.py` → `packages/erk-slots/src/erk_slots/navigation.py`:

- `execute_stack_navigation()` — main orchestrator
- `resolve_up_navigation()`, `resolve_down_navigation()`
- `find_worktree_for_branch_or_path()`, `WorktreeLookupResult`, `NavigationResult`
- `_activate_with_deferred_deletion()`
- `validate_for_deletion()`, `verify_pr_closed_or_merged()`
- `delete_branch_and_worktree()`, `unallocate_worktree_and_branch()`
- `render_deferred_deletion_commands()`, `get_slot_name_for_worktree()`

The new module imports shared functions from `erk.cli.commands.navigation_helpers` (activation, checks). This cross-package import pattern matches all existing erk_slots commands (confirmed: `common.py`, `checkout_cmd.py`, `unassign_cmd.py` all import from `erk.cli.*` and `erk.core.*`).

### 2. Create command files in erk_slots

**`packages/erk-slots/src/erk_slots/up_cmd.py`** — thin wrapper, mirrors current `up.py` but imports `execute_stack_navigation` from `erk_slots.navigation`.

**`packages/erk-slots/src/erk_slots/down_cmd.py`** — same pattern.

### 3. Register in slot group

**`packages/erk-slots/src/erk_slots/group.py`** — add:
```python
from erk_slots.up_cmd import slot_up
from erk_slots.down_cmd import slot_down
slot_group.add_command(slot_up)
slot_group.add_command(slot_down)
```

### 4. Trim `navigation_helpers.py`

Keep only shared functions used by other erk commands:
- `activate_target()`, `activate_worktree()`, `activate_root_repo()` — used by `land_cmd.py`, `wt/checkout_cmd.py`
- `check_clean_working_tree()` — used by `land_cmd.py`, `land_stack.py`, `land_pipeline.py`
- `check_pending_learn_marker()` — used by `wt/delete_cmd.py`
- `find_assignment_by_worktree_path()` — used by `wt/delete_cmd.py`, `branch/delete_cmd.py`, `stack/consolidate_cmd.py`

Remove navigation-specific functions and the `execute_unassign` import.

### 5. Delete old command files and CLI registration

- Delete `src/erk/cli/commands/up.py`
- Delete `src/erk/cli/commands/down.py`
- Remove from `src/erk/cli/cli.py`: imports of `up_cmd`/`down_cmd` (lines 19, 37) and `cli.add_command` calls (lines 192, 209)

No backwards-compatibility shims (per project constraints).

### 6. Update tests

**Command tests** — change CLI invocation paths:
- `tests/commands/navigation/test_up.py`: `["up", ...]` → `["slot", "up", ...]` (~25 invocations)
- `tests/commands/navigation/test_down.py`: `["down", ...]` → `["slot", "down", ...]` (~27 invocations)
- `tests/commands/navigation/test_stack_navigation.py`: same pattern (~10 invocations)

**Unit tests** — split `tests/unit/cli/test_navigation_helpers.py`:
- Functions tested: `delete_branch_and_worktree`, `validate_for_deletion`, `render_deferred_deletion_commands`, `unallocate_worktree_and_branch`, `get_slot_name_for_worktree` → move to `packages/erk-slots/tests/unit/test_navigation.py`, update imports to `erk_slots.navigation`
- Functions tested: `activate_root_repo` → stays (imported from `erk.cli.commands.navigation_helpers`)

**Unchanged:** `tests/unit/cli/commands/land/test_find_assignment.py` — imports `find_assignment_by_worktree_path` from `navigation_helpers` which stays.

## Files Modified

| File | Action |
|------|--------|
| `packages/erk-slots/src/erk_slots/navigation.py` | Create — navigation-specific functions |
| `packages/erk-slots/src/erk_slots/up_cmd.py` | Create — `slot up` command |
| `packages/erk-slots/src/erk_slots/down_cmd.py` | Create — `slot down` command |
| `packages/erk-slots/src/erk_slots/group.py` | Edit — register up/down commands |
| `src/erk/cli/commands/navigation_helpers.py` | Edit — remove navigation-specific functions |
| `src/erk/cli/commands/up.py` | Delete |
| `src/erk/cli/commands/down.py` | Delete |
| `src/erk/cli/cli.py` | Edit — remove up_cmd/down_cmd imports and registration |
| `tests/commands/navigation/test_up.py` | Edit — `["up"` → `["slot", "up"` |
| `tests/commands/navigation/test_down.py` | Edit — `["down"` → `["slot", "down"` |
| `tests/commands/navigation/test_stack_navigation.py` | Edit — same pattern |
| `tests/unit/cli/test_navigation_helpers.py` | Edit — remove navigation-specific tests |
| `packages/erk-slots/tests/unit/test_navigation.py` | Create — moved navigation tests |

## Verification

1. Run navigation tests: `uv run pytest tests/commands/navigation/ -x`
2. Run moved unit tests: `uv run pytest packages/erk-slots/tests/unit/test_navigation.py -x`
3. Run remaining navigation_helpers tests: `uv run pytest tests/unit/cli/test_navigation_helpers.py -x`
4. Run land tests (ensure shared functions still work): `uv run pytest tests/commands/land/ -x`
5. Run full fast-ci: `make fast-ci`
6. Grep for stale imports: `rg "from erk.cli.commands.(up|down) import"` and `rg "from erk.cli.commands.navigation_helpers import execute_stack_navigation"`

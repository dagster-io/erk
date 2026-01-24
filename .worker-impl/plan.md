# Delete Slot-Level Objective ID Metadata

## Summary

Remove the `last_objective_id` field from `SlotInfo` and all related storage/retrieval code. This eliminates slot-level objective tracking while preserving plan-level objective linking (the `objective_issue` field in plan-header metadata).

## Scope

**DELETE:** Slot-level objective tracking (`last_objective_id` in pool.json slots)
**KEEP:** Plan-level objective linking (`objective_issue` in GitHub plan issue metadata)

---

## Phase 1: Delete Slot Objective Exec Script

### Files to DELETE:
- `src/erk/cli/commands/exec/scripts/slot_objective.py`
- `tests/unit/cli/commands/exec/scripts/test_slot_objective.py`

### Files to MODIFY:
- `src/erk/cli/commands/exec/group.py`:
  - Remove import of `slot_objective`
  - Remove `exec_group.add_command(slot_objective, name="slot-objective")`

---

## Phase 2: Remove `last_objective_id` from SlotInfo

### File: `src/erk/core/worktree_pool.py`

1. Remove `last_objective_id: int | None` field from `SlotInfo` dataclass (line 28)
2. Update docstring to remove reference to `last_objective_id` (lines 23-24)
3. Delete `update_slot_objective()` function entirely (lines 156-188)
4. Update `load_pool_state()`: change line 105 from `SlotInfo(name=s["name"], last_objective_id=s.get("last_objective_id"))` to `SlotInfo(name=s["name"])`
5. Update `save_pool_state()`: change line 141 from `[{"name": s.name, "last_objective_id": s.last_objective_id} for s in state.slots]` to `[{"name": s.name} for s in state.slots]`

### File: `tests/unit/core/test_worktree_pool.py`
- Remove import of `update_slot_objective` (line 11)
- Update all `SlotInfo()` calls to remove `last_objective_id` argument (lines 102-103, 162, 170, 178-179, 200-201, 237-238, 249, 259, 269, 295)
- Delete tests for `update_slot_objective()` (lines 235-313):
  - `test_update_slot_objective_sets_value`
  - `test_update_slot_objective_clears_value`
  - `test_update_slot_objective_replaces_value`
  - `test_update_slot_objective_creates_slot_if_not_found`
  - `test_update_slot_objective_creates_slot_in_empty_pool`
  - `test_update_slot_objective_preserves_other_fields`
- Delete tests that reference `last_objective_id` (lines 160-232):
  - `test_slot_info_creation` - update to remove assertion
  - `test_slot_info_with_objective` - DELETE entirely
  - `test_pool_state_with_slots_no_assignments` - update fixtures
  - `test_save_and_load_pool_state_with_objective` - DELETE entirely
  - `test_load_pool_state_missing_objective_field` - DELETE entirely

### File: `tests/unit/cli/commands/slot/test_common.py`
- Update all `SlotInfo()` calls to remove `last_objective_id` argument (lines 340, 347, 406, 417, 419, 435-436)

---

## Phase 3: Remove Slot Objective Update from Plan Save

### File: `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

1. Remove imports at lines 32-36 (keep `load_pool_state` if needed elsewhere, remove `save_pool_state` and `update_slot_objective`)
2. Delete `_detect_current_slot()` function (lines 90-118)
3. Delete `_update_slot_objective_if_applicable()` function (lines 121-147)
4. Remove lines 351-354 (slot objective update call)
5. Remove lines 368-369 and 381-383 (slot_name from output)

### File: `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`
- Remove tests related to slot objective updates

---

## Phase 4: Remove Slot Objective Update from Land Command

### File: `src/erk/cli/commands/land_cmd.py`

1. Remove `update_slot_objective` from import at line 49
2. Remove objective recording logic in `_cleanup_slot_with_assignment()` at lines 446-452:
   ```python
   # Record objective on slot BEFORE unassigning (so it persists after assignment removed)
   if cleanup.objective_number is not None:
       updated_state = update_slot_objective(state, assignment.slot_name, cleanup.objective_number)
       ...
   ```

Note: Keep `get_objective_for_branch()` and `prompt_objective_update()` - these use plan-level objective linking, not slot-level.

---

## Phase 5: Update Documentation

### File: `docs/learned/erk/slot-pool-architecture.md`
- Remove documentation about slot-level objective tracking (`last_objective_id`)

---

## Critical Files

| File | Purpose |
|------|---------|
| `src/erk/core/worktree_pool.py` | Core `SlotInfo` dataclass and `update_slot_objective()` |
| `src/erk/cli/commands/exec/scripts/slot_objective.py` | Exec script to query slot's objective (DELETE) |
| `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` | Updates slot objective on plan save |
| `src/erk/cli/commands/land_cmd.py` | Updates slot objective on land |

---

## Verification

Run `devrun` agent with `make fast-ci` after each phase.

Final verification:
```bash
grep -r "last_objective_id" src/ tests/
grep -r "update_slot_objective" src/ tests/
grep -r "slot_objective" src/ tests/
```

All should return no matches.
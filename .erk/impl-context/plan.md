# Rename deps-state/deps columns to head-state/head in Objectives dashboard

## Context

The objectives dashboard (`erk dash`, tab 3) has two columns — `deps-state` and `deps` — that surface the leading-edge work item for each objective. The current naming is confusing: "in progress" reads as if it describes the objective itself, and "deps" is implementation jargon. We agreed on a "head" metaphor (like git HEAD — the current position) with values `active`/`ready`/`-`.

## Changes

### 1. Rename dataclass fields in `PlanRowData`

**File:** `src/erk/tui/data/types.py`

- `objective_deps_display` → `objective_head_state`
- `objective_deps_plans` → `objective_head_plans`
- Update docstrings accordingly (replace "Dep status" with "Head state", update value examples to use "active")

### 2. Rename column headers in TUI table

**File:** `src/erk/tui/widgets/plan_table.py`

- Column label `"deps-state"` → `"head-state"`, key `"deps_state"` → `"head_state"`
- Column label `"deps"` → `"head"`, key `"deps"` → `"head"`
- Rename `_deps_column_index` → `_head_column_index`
- Update comment on row tuple ordering
- Update all references to the renamed fields

### 3. Change "in progress" display value to "active"

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Line 701: Replace `min_status.replace("_", " ")` with a mapping that converts `"in_progress"` → `"active"` (other statuses like "pending", "blocked", "planning" remain as-is via underscore replacement)
- Rename local variable `objective_deps_display` → `objective_head_state`
- Rename local variable `objective_deps_plans` → `objective_head_plans`
- Update kwarg names in `PlanRowData(...)` construction

### 4. Update fake provider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

- Rename parameter `objective_deps_display` → `objective_head_state`
- Rename parameter `objective_deps_plans` → `objective_head_plans`
- Update docstrings (replace "in progress" example with "active")

### 5. Update app.py references

**File:** `src/erk/tui/app.py`

- `row.objective_deps_plans` → `row.objective_head_plans`

### 6. Update dash_data.py serialization

**File:** `src/erk/cli/commands/exec/scripts/dash_data.py`

- `row.objective_deps_plans` → `row.objective_head_plans`
- Update dict key `"objective_deps_plans"` → `"objective_head_plans"`

### 7. Update tests

**Files:**
- `tests/tui/data/test_provider.py` — rename field references, update "in progress" assertions to "active"
- `tests/tui/test_plan_table.py` — rename field references, update comments ("deps-state" → "head-state")
- `tests/tui/commands/test_execute_command.py` — rename kwarg names
- `tests/unit/cli/commands/exec/scripts/test_dash_data.py` — rename kwarg names and serialization key assertions

## Verification

1. Run `make fast-ci` to validate all tests pass
2. Run `erk dash -i` and verify tab 3 shows `head-state` and `head` columns with `active`/`ready` values

# Plan: Extend Roadmap Table with Type and Depends On Columns

**Part of Objective #6629, Steps 1.1 + 1.2**

## Goal

Add `Type` and `Depends On` columns to the objective roadmap table format, with full backwards compatibility for existing 4-column tables.

**New 6-column format:**
```markdown
| Step | Description | Type | Depends On | Status | PR |
|------|-------------|------|------------|--------|-----|
| 1.1 | Setup infra | plan | | pending | |
| 1.2 | Add module | objective | | pending | |
| 1.3 | Wire together | plan | 1.1, 1.2 | pending | |
```

**Old 4-column format continues to work** with defaults: `step_type="plan"`, `depends_on=[]`.

## Design Decisions

- **Dual header detection**: Parser checks for 6-column header first, falls back to 4-column
- **Cross-phase dependencies allowed**: Step 2.1 can depend on step 1.3
- **New fields always serialized**: JSON output always includes `step_type` and `depends_on` (stable schema)
- **No default parameter values**: New fields are required positional args on `RoadmapStep`

## Implementation

### 1. Update `RoadmapStep` dataclass

**File:** `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py`

Add two new fields:
- `step_type: str` — `"plan"` or `"objective"`
- `depends_on: list[str]` — e.g., `["1.1", "1.2"]`

### 2. Update `parse_roadmap` function

**File:** same

- Add 6-column header regex: `| Step | Description | Type | Depends On | Status | PR |`
- Try 6-col header first, fall back to 4-col (LBYL)
- Add 6-column row regex (6 capture groups)
- Parse `Type` column: normalize to `"plan"` or `"objective"`, default `"plan"`
- Parse `Depends On` column: split on commas, strip whitespace, treat `"-"` and empty as `[]`
- Update separator regex to handle 4-6 columns
- Pass new fields to `RoadmapStep` constructor

### 3. Update `serialize_phases` and `find_next_step`

**File:** same

- `serialize_phases`: add `step_type` and `depends_on` to step dict
- `find_next_step`: add `step_type` to returned dict

### 4. Update `_replace_step_pr_in_body`

**File:** `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`

- Try 6-column row regex first (preserves Type and Depends On cells, replaces Status and PR)
- Fall back to 4-column row regex
- Order matters: 4-col regex would incorrectly match first 4 cells of a 6-col row

### 5. Add new validation checks

**File:** `src/erk/cli/commands/objective/check_cmd.py`

- **Check 6**: Depends On references valid step IDs (across all phases)
- **Check 7**: Step type values are `"plan"` or `"objective"` (safety net)

### 6. Update tests

**Files:**
- `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py`
- `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py`
- `tests/unit/cli/commands/objective/test_check_cmd.py`

**Test updates:**
- Fix all direct `RoadmapStep(...)` constructions to include new required fields
- Add: 6-column table parsing test
- Add: 4-column backwards compatibility test (default values)
- Add: 6-column status inference test
- Add: depends_on with dash/empty yields `[]`
- Add: serialize includes new fields
- Add: update step in 6-col table preserves Type and Depends On
- Add: invalid depends_on reference fails validation
- Add: cross-phase dependency passes validation
- Add: JSON output includes new fields from 6-col table

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` | Dataclass + parser |
| `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` | Dual-format row regex |
| `src/erk/cli/commands/objective/check_cmd.py` | 2 new validation checks |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py` | New tests + fix constructors |
| `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py` | 6-col update tests |
| `tests/unit/cli/commands/objective/test_check_cmd.py` | Dependency validation tests |

## Verification

1. Run parser tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py -v`
2. Run update tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py -v`
3. Run check tests: `uv run pytest tests/unit/cli/commands/objective/test_check_cmd.py -v`
4. Run type checker: `uv run ty check src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py`
5. Validate against real objective: `erk objective check 6629 --json-output` (existing 4-col table should pass)
6. Run full CI: `make fast-ci`
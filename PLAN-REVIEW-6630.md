# Plan: Extend Roadmap Table with Type and Depends On Columns

**Part of Objective #6629, Steps 1.1 + 1.2**

## Goal

Add `Type` and `Depends On` columns to the objective roadmap table format, with full backwards compatibility for existing 4-column tables.

**New 7-column format:**
```markdown
| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Setup infra | plan | #6630 | | done | #6631 |
| 1.2 | Add module | objective | #7001 | | pending | |
| 1.3 | Wire together | plan | | 1.1, 1.2 | pending | |
```

The `Issue` column stores the linked GitHub issue number for the step — plan issues for `plan` type steps, child objective issues for `objective` type steps. The `PR` column stores the associated PR (implementation PR for plans, or empty for objectives).

**Old 4-column format continues to work** with defaults: `step_type="plan"`, `depends_on=[]`, `issue=None`.

## Design Decisions

- **Dual header detection**: Parser checks for 6-column header first, falls back to 4-column
- **Cross-phase dependencies allowed**: Step 2.1 can depend on step 1.3
- **New fields always serialized**: JSON output always includes `step_type` and `depends_on` (stable schema)
- **No default parameter values**: New fields are required positional args on `RoadmapStep`
- **Issue column for all step types**: The `Issue` column links to the step's GitHub issue — plan issues for `plan` steps, child objective issues for `objective` steps. The `PR` column stores the associated implementation PR.

## Implementation

### 1. Update `RoadmapStep` dataclass

**File:** `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py`

Add three new fields:
- `step_type: str` — `"plan"` or `"objective"`
- `issue: str | None` — e.g., `"#7001"` for sub-objective steps, `None` otherwise
- `depends_on: list[str]` — e.g., `["1.1", "1.2"]`

### 2. Update `parse_roadmap` function

**File:** same

- Add 7-column header regex: `| Step | Description | Type | Issue | Depends On | Status | PR |`
- Try 7-col header first, fall back to 4-col (LBYL)
- Add 7-column row regex (7 capture groups)
- Parse `Type` column: normalize to `"plan"` or `"objective"`, default `"plan"`
- Parse `Issue` column: store `"#NNN"` or `None` (treat `"-"` and empty as `None`)
- Parse `Depends On` column: split on commas, strip whitespace, treat `"-"` and empty as `[]`
- Update separator regex to handle 4 or 7 columns
- Pass new fields to `RoadmapStep` constructor

### 3. Update `serialize_phases` and `find_next_step`

**File:** same

- `serialize_phases`: add `step_type`, `issue`, and `depends_on` to step dict
- `find_next_step`: add `step_type` to returned dict

### 4. Update `_replace_step_pr_in_body`

**File:** `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`

- Try 7-column row regex first (preserves Type, Issue, and Depends On cells, replaces Status and PR)
- Fall back to 4-column row regex
- Order matters: 4-col regex would incorrectly match first 4 cells of a 7-col row
- Note: The existing command updates the PR cell. The Issue cell is updated by `plan-save` (via a separate mechanism in a later step of the objective). For this PR, the Issue column is preserved as-is during PR cell updates.

### 5. Update `erk objective check` validation

**File:** `src/erk/cli/commands/objective/check_cmd.py`

The `erk objective check` command (`validate_objective()`) validates roadmap format and consistency. It currently runs 5 checks. This plan adds two new checks to validate the new columns:

- **Check 6**: Depends On references valid step IDs (across all phases)
- **Check 7**: Step type values are `"plan"` or `"objective"` (safety net)

Existing checks (label, parsing, status/PR consistency, orphaned done, phase numbering) continue to work unchanged since `parse_roadmap` handles both 4-col and 7-col formats.

### 6. Update tests

**Files:**
- `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py`
- `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py`
- `tests/unit/cli/commands/objective/test_check_cmd.py`

**Test updates:**
- Fix all direct `RoadmapStep(...)` constructions to include new required fields
- Add: 7-column table parsing test (including Issue column)
- Add: 4-column backwards compatibility test (default values)
- Add: 7-column status inference test
- Add: depends_on with dash/empty yields `[]`
- Add: issue column with dash/empty yields `None`
- Add: serialize includes new fields (step_type, issue, depends_on)
- Add: update step in 7-col table preserves Type, Issue, and Depends On
- Add: invalid depends_on reference fails validation
- Add: cross-phase dependency passes validation
- Add: JSON output includes new fields from 7-col table

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` | Dataclass + parser |
| `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` | Dual-format row regex (4-col and 7-col) |
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
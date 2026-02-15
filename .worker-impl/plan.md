# Remove Legacy Objective Roadmap Format Support

## Context

Objective roadmaps historically supported three formats:
1. **Legacy 4-column table**: `| Step | Description | Status | PR |` with `plan #NNN` encoded in the PR column
2. **5-column table**: `| Step | Description | Status | Plan | PR |` with separate columns
3. **YAML frontmatter v2**: The current format, stored in `<!-- erk:metadata-block:objective-roadmap -->` blocks

All production objectives now use YAML frontmatter v2. The table parsing fallback and v1 frontmatter migration code are dead code paths that add maintenance burden and test complexity. This cleanup removes all legacy parsing, making frontmatter v2 the sole supported format.

**Important distinction**: Table *parsing* (reading data FROM tables) is removed. Table *sync* (writing updated data TO the rendered markdown table) is kept — the table is still rendered for human readability.

## Changes

### 1. Remove table fallback from `parse_roadmap()`
**File**: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py`

- Delete lines 116-255 (the entire `# Fall back to table parsing` block)
- When no frontmatter block exists or frontmatter is invalid, return `([], ["No objective-roadmap frontmatter block found"])`
- Remove `cast` from the `typing` import (only used in table fallback)
- Update module docstring and `parse_roadmap()` docstring to remove "falls back to table parsing" language

### 2. Remove v1 schema support from frontmatter validation
**File**: `src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py`

- `validate_roadmap_frontmatter()`: Change version check from `not in ("1", "2")` to `!= "2"` (line 46)
- Remove `is_v2` variable (line 50)
- Remove v1 migration block (lines 104-109): the `if not is_v2 and isinstance(raw_pr, str) and raw_pr.startswith("plan #"):` branch
- Update docstring to reflect v2-only support

### 3. Remove `_STALE_STATUS_4COL` from check command
**File**: `src/erk/cli/commands/objective/check_cmd.py`

- Delete `_STALE_STATUS_4COL` regex (lines 26-31) and its comment
- Update comment on `_STALE_STATUS_5COL` (remove "in both 4-col and" language)
- Line 172: Change `_STALE_STATUS_4COL.findall(issue.body) + _STALE_STATUS_5COL.findall(issue.body)` to just `_STALE_STATUS_5COL.findall(issue.body)`

### 4. Update comments in `_replace_step_refs_in_body()`
**File**: `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`

- Update docstring at line 142 to remove "Falls back to regex table replacement for backward compatibility" — replace with "Also updates the rendered markdown table to keep it in sync"
- Update comment at line 204 to remove "either as fallback or" — just "to keep in sync"
- No functional changes — table sync code is kept

### 5. Convert `test_update_roadmap_step.py` fixtures to frontmatter
**File**: `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py`

- Replace `ROADMAP_BODY_5COL` fixture (lines 13-32) with a new fixture that includes both a frontmatter block AND rendered table (matching the pattern of `FRONTMATTER_ROADMAP_BODY` already in the file at line 209)
- Delete `test_fallback_to_table_when_no_frontmatter` (lines 291-309) — tests a removed code path
- Delete `test_explicit_status_option_table_only` (lines 312-331) — tests table-only path; `test_explicit_status_option_with_frontmatter` already covers this
- All ~18 other tests using `ROADMAP_BODY_5COL` will automatically use the new frontmatter fixture

### 6. Convert `test_objective_roadmap_shared.py` tests
**File**: `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py`

- Replace `WELL_FORMED_BODY_5COL` fixture with a frontmatter version (frontmatter block + rendered table)
- Delete or convert table-only tests:
  - `test_parse_roadmap_5col_well_formed` → keep, now tests frontmatter parsing
  - `test_parse_roadmap_5col_plan_and_pr_values` → keep, now tests frontmatter values
  - `test_parse_roadmap_5col_status_inference` → keep, now tests frontmatter status
  - `test_parse_roadmap_sub_phases` → convert inline body to include frontmatter
  - `test_parse_roadmap_no_phases` → keep as-is (tests "No roadmap here" body)
  - `test_parse_roadmap_missing_table` → update: this now fails with "no frontmatter" error instead of "missing roadmap table"
  - `test_parse_roadmap_explicit_done_status` through `test_parse_roadmap_explicit_status_overrides_inference` → convert inline bodies to include frontmatter
  - `test_parse_roadmap_frontmatter_preferred` → keep but update v1→v2 schema
  - `test_parse_roadmap_no_frontmatter_fallback` → DELETE (tests removed fallback)
  - `test_parse_roadmap_invalid_frontmatter_fallback` → DELETE (tests removed fallback)
  - `test_parse_roadmap_planning_status_recognized` → convert to frontmatter
  - `test_parse_roadmap_v1_frontmatter_migrates_plan` → DELETE (tests removed v1 migration)

### 7. Convert `test_objective_roadmap_frontmatter.py` v1 tests
**File**: `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py`

- Delete `test_parse_valid_v1_frontmatter` (lines 13-45) — tests removed v1 parsing
- Update `test_parse_wrong_schema_version` docstring: "not '1' or '2'" → "not '2'"
- Convert remaining test fixtures that use `schema_version: "1"` to `schema_version: "2"`:
  - `test_parse_steps_not_list` (line 136)
  - `test_parse_missing_required_field` (line 148)
  - `test_update_step_in_frontmatter` (line 259) — also add `plan: null` fields to steps
  - `test_update_step_in_frontmatter_not_found` (line 291) — add `plan: null`
  - `test_update_step_with_trailing_content` (line 350) — add `plan: null`
  - `test_parse_handles_extra_fields` (line 373) — add `plan: null`
  - `test_update_step_with_explicit_status` (line 478) — add `plan: null`
  - `test_update_step_status_none_infers_from_pr` (line 498) — add `plan: null`
- Update validate tests:
  - `test_validate_roadmap_frontmatter_missing_step_field` (line 447) — change schema to "2"
  - `test_validate_roadmap_frontmatter_steps_not_list` (line 461) — change schema to "2"

### 8. Convert `test_check_cmd.py` fixtures to frontmatter
**File**: `tests/unit/cli/commands/objective/test_check_cmd.py`

- Replace `VALID_OBJECTIVE_BODY` (lines 43-62) with a version that includes a frontmatter block
- Convert all inline test bodies that use table-only format to include frontmatter blocks (tests at lines: 162, 221, 253, 285, 347, 377, 407)
- These tests now exercise frontmatter parsing instead of table parsing

### 9. Convert `test_next_plan_one_shot.py` fixtures to frontmatter
**File**: `tests/commands/objective/test_next_plan_one_shot.py`

- Replace `OBJECTIVE_BODY` (lines 15-31) with frontmatter version
- Replace `OBJECTIVE_ALL_DONE_BODY` (lines 33-43) with frontmatter version
- Convert inline body in `test_next_plan_one_shot_auto_detects_next_step` (line 171) to frontmatter

## Files Modified (Summary)

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` | Remove table fallback (~140 lines), remove `cast` import |
| `src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py` | Remove v1 support (~10 lines) |
| `src/erk/cli/commands/objective/check_cmd.py` | Remove `_STALE_STATUS_4COL` (~5 lines) |
| `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` | Update comments only |
| `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py` | Convert fixture, delete 2 tests |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py` | Convert fixtures, delete 3 tests, update assertions |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py` | Delete 1 test, convert ~10 fixtures v1→v2 |
| `tests/unit/cli/commands/objective/test_check_cmd.py` | Convert all fixtures to frontmatter |
| `tests/commands/objective/test_next_plan_one_shot.py` | Convert all fixtures to frontmatter |

## Verification

1. Run scoped unit tests: `pytest tests/unit/cli/commands/exec/scripts/ tests/unit/cli/commands/objective/ tests/commands/objective/`
2. Run `make all-ci` for full validation
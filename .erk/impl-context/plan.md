# Plan: Sweep plan_number/plan_id refs in land pipeline, implement, and core modules

**Objective:** #9109, Node 3.6.1
**Scope:** Rename `plan_id`, `plan_number`, and `plan_summary` field/parameter/variable names to `pr_id`, `pr_number`, and `pr_summary` in land pipeline, implement, and core modules.

## Context

This is part of the ongoing "plan → pr" terminology rename (objective #9109). Prior phases renamed gateway ABCs, JSON output fields, TypedDict fields, Click arguments, help strings, and TUI types. This node sweeps the remaining internal Python identifiers in the land pipeline, implement commands, and core utility modules.

**Out of scope:** Submit pipeline/dispatch/PlanContext (node 3.6.2), exec scripts (node 3.6.3), test fixture updates beyond what's needed to keep CI green (node 4.1).

## Rename Mapping

| Current | New | Type | Rationale |
|---------|-----|------|-----------|
| `LandState.plan_id` | `LandState.pr_id` | field (str\|None) | Avoids conflict with existing `LandState.pr_number: int` |
| `LandStackEntry.plan_id` | `LandStackEntry.pr_id` | field (str\|None) | Same pattern |
| `resolve_plan_id()` | `resolve_pr_id()` | function | Renames with field |
| `TargetInfo.plan_number` | `TargetInfo.pr_number` | field (str\|None) | Direct rename |
| target_type `"plan_number"` | `"pr_number"` | string literal | Discriminator value |
| target_type `"plan_url"` | `"pr_url"` | string literal | Discriminator value |
| `DuplicateMatch.plan_id` | `DuplicateMatch.pr_id` | field (str) | Direct rename |
| `format_worktree_line(plan_summary=)` | `format_worktree_line(pr_summary=)` | parameter | Direct rename |
| `_execute_land(plan_number=)` | `_execute_land(linked_pr_number=)` | parameter (int\|None) | Avoids conflict with existing `pr_number` param |
| `render_land_execution_script(plan_number=)` | `render_land_execution_script(linked_pr_number=)` | parameter (int\|None) | Same |
| Local `plan_id` variables | `pr_id` | local vars | Throughout all in-scope files |
| Local `plan_number` variables | `pr_number` or `pr_number_int` | local vars | Where no conflict exists |

## Source Files (11 files)

### Phase 1: Type definitions (4 files)

**1. `src/erk/cli/commands/land_pipeline.py`** (12 occurrences)
- Rename `LandState.plan_id` field → `pr_id`
- Rename function `resolve_plan_id` → `resolve_pr_id`
- Update all local vars, docstrings, and `dataclasses.replace()` calls
- Lines: 65, 341-351, 445, 486, 572, 591, 596, 622

**2. `src/erk/cli/commands/land_stack.py`** (4 occurrences)
- Rename `LandStackEntry.plan_id` field → `pr_id`
- Update constructor call and consumer: lines 46, 286, 528, 532

**3. `src/erk/cli/commands/implement_shared.py`** (8 occurrences)
- Rename `TargetInfo.plan_number` field → `pr_number`
- Rename target_type values: `"plan_number"` → `"pr_number"`, `"plan_url"` → `"pr_url"`
- Update `detect_target_type()` local var and all return statements
- Lines: 411-444

**4. `src/erk/core/plan_duplicate_checker.py`** (5 occurrences)
- Rename `DuplicateMatch.plan_id` field → `pr_id`
- Keep `entry.get("plan_id")` as-is (reads LLM JSON output)
- Update constructor: `DuplicateMatch(pr_id=plan_id, ...)`
- Lines: 47, 169-180

### Phase 2: Consumer modules (7 files)

**5. `src/erk/cli/commands/land_cmd.py`** (7 occurrences)
- Local `plan_id` → `pr_id` (lines 935, 951, 1054)
- Parameter `plan_number: int | None` → `linked_pr_number: int | None` in `_execute_land` and `render_land_execution_script` (lines 1313, 1420)
- Keep `--plan-number` CLI flag string (exec script scope, node 3.6.3)
- Update conversion: `plan_id=str(plan_number)` → `pr_id=str(linked_pr_number)` (line 1466)
- Lines: 935, 951, 1054, 1098, 1313, 1388-1389, 1420, 1445, 1466

**6. `src/erk/cli/commands/land_learn.py`** (25 occurrences)
- All `plan_id: str` parameters → `pr_id: str` across 7 functions
- All local `plan_id` variables → `pr_id`
- Functions: `_fetch_xmls_from_context_branch`, `_log_session_summary_from_manifest`, `_collect_session_material`, `_create_learn_pr_core`, `_create_learn_pr`, `create_learn_pr`, `_create_learn_pr_with_sessions`
- `state.plan_id` → `state.pr_id` (lines 438, 608)
- Git branch name `planned-pr-context/{pr_id}` — variable rename only, branch prefix unchanged

**7. `src/erk/cli/commands/implement.py`** (6 occurrences)
- `target_info.plan_number` → `target_info.pr_number`
- String literal checks: `"plan_number"` → `"pr_number"`, `"plan_url"` → `"pr_url"`
- Parameter `plan_number: str` → `pr_number: str` in `_implement_from_issue`

**8. `src/erk/core/display_utils.py`** (5 occurrences)
- Parameter `plan_summary` → `pr_summary` in `format_worktree_line()`
- Local var `plan_colored` → `pr_colored`
- Docstring updates
- Lines: 309, 326, 332, 398-401

**9. `src/erk/cli/commands/objective_helpers.py`** (6 occurrences)
- Local `plan_id` → `pr_id` (lines 34-35)
- Local `plan_number` → `pr_number_int` (line 38, avoids conflict with function param on line 79)
- Lines: 34-53

**10. `src/erk/cli/commands/pr/metadata_helpers.py`** (6 occurrences)
- Local `plan_id` → `pr_id` throughout both functions
- Lines: 43-51, 85-104

**11. `src/erk/cli/commands/wt/create_cmd.py`** (1 occurrence)
- `plan_id=str(setup.plan_number)` → `plan_id=str(setup.pr_number)` if setup field was renamed; otherwise update kwarg name if save_plan_ref accepts `pr_id`
- Verify what `save_plan_ref` expects before changing

## Test Files (9 files)

Tests must be updated to keep CI green after field renames.

**Land pipeline tests:**
1. `tests/unit/cli/commands/land/pipeline/test_resolve_plan_id.py` — rename file to `test_resolve_pr_id.py`, update all `plan_id=` kwargs and `result.plan_id` assertions
2. `tests/unit/cli/commands/land/pipeline/test_create_learn_issue.py` — update `plan_id=` kwargs in `_execution_state()`
3. `tests/unit/cli/commands/land/pipeline/test_validate_pr.py` — update `plan_id=None` in state construction
4. `tests/unit/cli/commands/land/pipeline/test_merge_pr.py` — update `plan_id=None` in state construction
5. `tests/unit/cli/commands/land/pipeline/test_run_execution_pipeline.py` — update `plan_id=None` in state construction (4 places)
6. `tests/unit/cli/commands/land/test_land_learn.py` — update all `plan_id=` kwargs (~30 places)

**Implement tests:**
7. `tests/commands/implement/test_target_detection.py` — update `.plan_number` → `.pr_number` and target_type string assertions

**Display utils tests:**
8. `tests/unit/test_display_utils.py` — update `plan_summary=` kwargs (4 places)
9. `tests/unit/core/test_display_utils.py` — update `plan_summary=` kwargs (4 places)

## Key Decisions

1. **`plan_id` → `pr_id` (not `pr_number`)**: `LandState` already has `pr_number: int`. The `plan_id` field is a `str | None`, so `pr_id` avoids type/name collision.
2. **`_execute_land(plan_number=)` → `linked_pr_number`**: This function already has a `pr_number: int | None` parameter. Using `linked_pr_number` distinguishes the two.
3. **Keep `--plan-number` CLI flag string**: The shell script generated by `render_land_execution_script` passes `--plan-number=N` to the exec script. Renaming the CLI flag is node 3.6.3 scope.
4. **Keep `entry.get("plan_id")` in plan_duplicate_checker**: This parses LLM JSON output where the key is defined in a prompt template. Only the dataclass field renames.
5. **Target type discriminators rename**: `"plan_number"` → `"pr_number"` and `"plan_url"` → `"pr_url"` since these are internal enum-like values.

## Implementation Order

1. `land_pipeline.py` — LandState field + resolve_plan_id function
2. `land_stack.py` — LandStackEntry field
3. `land_learn.py` — all plan_id parameters (highest occurrence count)
4. `land_cmd.py` — local vars + linked_pr_number params
5. `implement_shared.py` — TargetInfo field + discriminators
6. `implement.py` — consumer of TargetInfo
7. `display_utils.py` — plan_summary parameter
8. `plan_duplicate_checker.py` — DuplicateMatch field
9. `objective_helpers.py` — local variables
10. `metadata_helpers.py` — local variables
11. `wt/create_cmd.py` — verify and update kwarg
12. All test files — update kwargs and assertions
13. Verify with CI

## Verification

1. **Unit tests**: `make fast-ci` (runs ruff, ty, unit tests)
2. **Grep check**: Search for remaining `plan_id`, `plan_number`, `plan_summary` in the 11 source files to confirm completeness
3. **Full CI**: `make all-ci` for integration tests

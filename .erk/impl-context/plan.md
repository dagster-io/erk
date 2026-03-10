# Rename `plan-saved-issue` marker to `plan-saved`

## Context

The `plan-saved-issue` marker name incorrectly implies that plans are GitHub issues. Plans are actually PRs (draft pull requests). The marker stores the PR number and title of a saved plan for session deduplication. Renaming to `plan-saved` is clearer and consistent with the project's recent terminology migration from "issue" to "pr" for plans (see commit 27a8d08ef).

Note: `objective-saved-issue` is NOT renamed because objectives actually ARE GitHub issues, so that name is correct.

## Changes

### 1. Core marker implementation: `packages/erk-shared/src/erk_shared/scratch/session_markers.py`

**Rename marker file from `plan-saved-issue.marker` to `plan-saved.marker`:**

- Line 10: Update docstring reference from `plan-saved-issue.marker` to `plan-saved.marker`
- Line 63: Rename function `create_plan_saved_issue_marker` to `create_plan_saved_marker_with_title` (to avoid collision with existing `create_plan_saved_marker`)
  - Actually, better approach: rename to `create_plan_saved_pr_marker` — but wait, the prompt says rename to `plan-saved`. Let me reconsider.
  - The function `create_plan_saved_issue_marker` stores `{pr_number}\n{title}` in `plan-saved-issue.marker`. Rename the function to `create_plan_saved_dedup_marker` and the file to `plan-saved.marker`.
  - Actually, simplest: rename function to `create_plan_saved_pr_marker` and file to `plan-saved.marker`. The prompt says "change the name of the plan-saved-issue marker to just plan-saved."

**Specific changes:**
- Line 10: `plan-saved-issue.marker` -> `plan-saved.marker` in docstring
- Line 63-66: Rename `create_plan_saved_issue_marker` -> `create_plan_saved_pr_marker`
- Line 66: Update docstring: "Create marker file storing the PR number and title of the saved plan."
- Line 81: Change `"plan-saved-issue.marker"` -> `"plan-saved.marker"`
- Line 169: Rename `get_existing_saved_issue` -> `get_existing_saved_pr`
- Line 169: Update docstring references from "issue" to "PR"
- Line 185: Change `"plan-saved-issue.marker"` -> `"plan-saved.marker"`

### 2. Plan save script: `src/erk/cli/commands/exec/scripts/plan_save.py`

- Line 59: Update import `create_plan_saved_issue_marker` -> `create_plan_saved_pr_marker`
- Line 62: Update import `get_existing_saved_issue` -> `get_existing_saved_pr`
- Line 321: Update call `create_plan_saved_issue_marker(...)` -> `create_plan_saved_pr_marker(...)`
- Line 427: Update call `get_existing_saved_issue(...)` -> `get_existing_saved_pr(...)`

### 3. CLI marker help text: `src/erk/cli/commands/exec/scripts/marker.py`

- Line 114: Update docstring example from `plan-saved-issue` to `plan-saved` (in `marker_read` docstring)

### 4. Unit tests for session markers: `packages/erk-shared/tests/unit/scratch/test_session_markers.py`

- Line 7: Update import `create_plan_saved_issue_marker` -> `create_plan_saved_pr_marker`
- Line 10: Update import `get_existing_saved_issue` -> `get_existing_saved_pr`
- Line 90: Update comment `# create_plan_saved_issue_marker tests` -> `# create_plan_saved_pr_marker tests`
- Line 93: Rename test `test_create_plan_saved_issue_marker_stores_number_and_title` -> `test_create_plan_saved_pr_marker_stores_number_and_title`
- Line 97: Update call `create_plan_saved_issue_marker` -> `create_plan_saved_pr_marker`
- Line 100: Update assertion from `"plan-saved-issue.marker"` -> `"plan-saved.marker"`
- Line 106: Update comment `# get_existing_saved_issue tests` -> `# get_existing_saved_pr tests`
- Line 109: Rename test function `test_get_existing_saved_issue_returns_plan_number_for_same_title` -> `test_get_existing_saved_pr_returns_plan_number_for_same_title`
- Line 112, 114: Update calls
- Line 119: Rename test `test_get_existing_saved_issue_returns_none_for_different_title` -> `test_get_existing_saved_pr_returns_none_for_different_title`
- Line 122, 124: Update calls
- Line 129: Rename test `test_get_existing_saved_issue_returns_none_when_no_marker` -> `test_get_existing_saved_pr_returns_none_when_no_marker`
- Line 131: Update call
- Line 136: Rename test `test_get_existing_saved_issue_returns_none_for_non_numeric` -> `test_get_existing_saved_pr_returns_none_for_non_numeric`
- Line 141: Update marker filename `"plan-saved-issue.marker"` -> `"plan-saved.marker"`
- Line 144: Update call
- Line 149: Rename test `test_get_existing_saved_issue_old_format_backwards_compat` -> `test_get_existing_saved_pr_old_format_backwards_compat`
- Line 154: Update marker filename `"plan-saved-issue.marker"` -> `"plan-saved.marker"`
- Line 157: Update call
- Line 280, 283, 286, 289: Update calls in integration-style test

### 5. Unit tests for plan_save: `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

- Line 920: Update assertion from `"plan-saved-issue.marker"` -> `"plan-saved.marker"`

### 6. Unit tests for marker CLI: `tests/unit/cli/commands/exec/scripts/test_marker.py`

- Lines 171, 178, 182, 231, 238, 312, 319: Update all `plan-saved-issue` string references to `plan-saved`

### 7. Documentation: `docs/learned/planning/workflow-markers.md`

- Line 41: Update `--name plan-saved-issue` -> `--name plan-saved`
- Line 44: Update `--name plan-saved-issue` -> `--name plan-saved`
- Line 49: Update text referencing `plan-saved-issue` marker

### 8. Command: `.claude/commands/erk/plan-save.md`

- Line 229: Update `plan-saved-issue` -> `plan-saved`

### 9. Command: `.claude/commands/erk/pr-dispatch.md`

- Line 38: Update `plan-saved-issue` -> `plan-saved`

### 10. Skill: `.claude/skills/erk-planning/SKILL.md`

- Line 21, 23: Update `plan-saved-issue` references to `plan-saved`

### 11. Documentation: `docs/learned/planning/session-deduplication.md`

- Line 47: Update `_get_existing_saved_issue()` -> `_get_existing_saved_pr()` (or just `get_existing_saved_pr()`)
- Line 50: Update function reference
- Line 85: Update heading

### 12. Documentation: `docs/learned/planning/pr-submission-patterns.md`

- Line 35: Update comment reference
- Line 37: Update function name reference

## Files NOT changing

- `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py` — The `objective-saved-issue` marker is correctly named because objectives ARE GitHub issues
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` — This file references `exit-plan-mode-hook.plan-saved.marker` (a different marker) and `plan_saved_issue_marker` is not referenced here
- `packages/erk-shared/src/erk_shared/scratch/markers.py` — Worktree-scoped markers, unrelated

## Implementation Details

**Naming conventions:**
- Marker file: `plan-saved-issue.marker` -> `plan-saved.marker`
- Python function: `create_plan_saved_issue_marker` -> `create_plan_saved_pr_marker`
- Python function: `get_existing_saved_issue` -> `get_existing_saved_pr`
- No backwards compatibility shims — break and migrate immediately per erk convention

**No runtime migration needed:** Marker files are session-scoped and ephemeral. Any existing `plan-saved-issue.marker` files will be in stale sessions and safely ignored. No migration code is needed.

## Verification

1. Run `ruff check` to verify no import errors
2. Run `ty check` to verify type correctness
3. Run `pytest tests/unit/cli/commands/exec/scripts/test_marker.py` — marker CLI tests pass
4. Run `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py` — plan save tests pass
5. Run `pytest packages/erk-shared/tests/unit/scratch/test_session_markers.py` — session marker tests pass
6. Grep for any remaining `plan-saved-issue` references to confirm none were missed
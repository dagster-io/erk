# Fix: Include branch_name in skipped_duplicate plan-save response

## Context

When `erk exec plan-save` detects a duplicate (same session already saved a plan), it returns a minimal JSON response with only `plan_number`, `skipped_duplicate`, and `message` — no `branch_name`, `plan_url`, or `plan_backend`. The plan-save command instructions then tell Claude to display next steps using `<branch_name>` from the JSON, but since it's missing, Claude fabricates a branch name based on the naming pattern. The user then tries to check out a branch that doesn't exist.

The root cause: when `skipped_duplicate: true`, the branch_name is never returned in the JSON, and the command instructions have no handling for the duplicate case.

## Plan

### 1. Add branch marker to session markers

**File:** `packages/erk-shared/src/erk_shared/scratch/session_markers.py`

- Add `create_plan_saved_branch_marker(session_id, repo_root, branch_name)` — writes branch name to `plan-saved-branch.marker`
- Add `get_existing_saved_branch(session_id, repo_root) -> str | None` — reads branch name from marker

### 2. Write branch marker during plan save

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

In `_save_as_draft_pr()` (around line 252, after `create_plan_saved_issue_marker`):
- Call `create_plan_saved_branch_marker(session_id, repo_root, branch_name)`

### 3. Include branch_name in skipped_duplicate response

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

In `_save_plan_via_draft_pr()` dedup path (lines 313-334):
- After detecting duplicate, also read `get_existing_saved_branch(session_id, repo_root)`
- Include `branch_name` (if found) and `plan_backend: "draft_pr"` in the JSON response

### 4. Add skipped_duplicate handling to command instructions

**File:** `.claude/commands/erk/plan-save.md`

In Step 4 (Display Results), add handling before the success case:

```
If JSON contains `skipped_duplicate: true`:
  Display: "Plan already saved as #<plan_number> (duplicate skipped)"
  If `branch_name` is present, display the same next-steps block as the success case
  If `branch_name` is absent, display only: "View PR: gh pr view <plan_number> --web"
  Return (skip Steps 3, 3.5)
```

## Verification

1. Run unit tests for session markers: `pytest tests/unit/ -k "plan_saved_branch"`
2. Run unit tests for plan_save: `pytest tests/unit/cli/commands/exec/scripts/ -k "plan_save"`
3. Manual test: save a plan, then call plan-save again — verify the duplicate response includes `branch_name`

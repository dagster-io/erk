# Plan: Add `--description` to roadmap update + skill instructions for stale descriptions

## Problem

When PR #6433 landed, step 1.1 in objective #6423 still says "Add `erk dash-data --json` CLI command" but the actual implementation is `erk exec dash-data`. Two gaps:

1. `objective-roadmap-update` has no `--description` flag — can't update step text
2. The `objective-update-with-landed-pr` skill doesn't tell the agent to detect/fix stale descriptions

## Changes

### 1. Add `--description` to `objective-roadmap-update`

**File:** `src/erk/cli/commands/exec/scripts/objective_roadmap_update.py`

- Add `--description` Click option (optional, like `--status` and `--pr`)
- Update validation: at least one of `--status`, `--pr`, or `--description` must be provided
- In `_replace_row_cells`, accept optional `description` parameter; if provided, use it instead of preserving original
- Return updated step data in JSON output as before

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_update.py`

- Add test: `test_update_description_only` — update description, verify status/PR preserved
- Add test: `test_update_description_with_pr` — update both description and PR together
- Add test: `test_no_flags_provided` — verify error when no flags given (update existing test if needed to cover `--description`)

### 2. Update skill to detect and fix stale descriptions

**File:** `.claude/commands/erk/objective-update-with-landed-pr.md`

Add instruction in Step 6 (after the `erk exec objective-roadmap-update` call) telling the agent to:

1. Compare the PR title against the step description
2. If they meaningfully differ (e.g., command location changed, scope changed), pass `--description` to update the step text
3. Keep descriptions concise — match the style of other steps in the roadmap

### 3. Update exec reference

**File:** `.claude/skills/erk-exec/reference.md`

- Add `--description` to the `objective-roadmap-update` command signature

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_roadmap_update.py`
2. Type check: `ty check src/erk/cli/commands/exec/scripts/objective_roadmap_update.py`
3. Lint: `ruff check src/erk/cli/commands/exec/scripts/objective_roadmap_update.py`

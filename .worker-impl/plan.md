# Plan: Fix Plan Save Workflow Bugs

## Problem

Issues #5928 and #5929 were created as objectives (with `erk-objective` label) when they should have been plans (with `erk-plan + erk-learn` labels). Root cause: workflow gaps caused agent confusion.

## Bugs to Fix

### 1. `/erk:plan-save` missing `--plan-type` support

**Location:** `.claude/commands/erk/plan-save.md`

The `/erk:replan` skill tells agents to use `--plan-type=learn`, but `/erk:plan-save` doesn't parse or forward this flag. The underlying `erk exec plan-save-to-issue` DOES support it.

**Fix:** Update skill to:
- Document `--plan-type=learn` in Usage section
- Parse `--plan-type` from `$ARGUMENTS` in Step 1
- Pass `--plan-type=learn` to exec command in Step 2

### 2. Misleading docstring in `objective_save_to_issue.py`

**Location:** `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py:54`

**Current:** "Creates a GitHub issue with erk-plan + erk-objective labels"
**Actual:** Creates issue with ONLY `erk-objective` label

**Fix:** Update docstring to: "Creates a GitHub issue with only the erk-objective label (NOT erk-plan)."

### 3. Missing idempotency in `objective_save_to_issue.py`

**Location:** `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`

`plan_save_to_issue.py` has `_get_existing_saved_issue()` to prevent duplicate creation. `objective_save_to_issue.py` lacks this protection, allowing duplicates like #5928/#5929.

**Fix:** Add session-based deduplication:
- Create `_create_objective_saved_issue_marker()`
- Create `_get_existing_saved_objective()` check
- Call dedup check before creating issue

## Files to Modify

1. `.claude/commands/erk/plan-save.md` - Add `--plan-type` support
2. `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py` - Fix docstring + add idempotency

## Verification

1. Run `/erk:plan-save --plan-type=learn` and verify issue gets `erk-plan + erk-learn` labels
2. Run `erk exec objective-save-to-issue` twice with same session-id, verify second call returns existing issue
3. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_save_to_issue.py -v`
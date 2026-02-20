# Plan: Make `erk pr check` Respect Draft PR Conventions

## Context

`erk pr check` fails for draft-PR plans because it unconditionally requires a "Closes #N" reference in the PR body whenever a `plan_ref` exists. For draft-PR plans, the PR IS the plan — adding "Closes #7656" to PR #7656 would self-close the plan. Two other code paths already handle this correctly (`get_closing_text.py:85-89`, `submit_pipeline.py:645-651`), but `check_cmd.py` does not.

## Changes

### 1. Modify `src/erk/cli/commands/pr/check_cmd.py` (lines 70-90)

Add a provider check before the closing reference validation. When `plan_ref.provider == "github-draft-pr"`, append a PASS check with message "Draft PR plan — no closing reference needed" instead of checking for "Closes #N".

The existing else-branch (issue-based plans) is preserved exactly. No new imports needed — `read_plan_ref` is already imported and `PlanRef.provider` is already available.

### 2. Add test to `tests/commands/pr/test_check.py`

Add `test_pr_check_passes_for_draft_pr_plan` using:

- `plan-ref.json` with `"provider": "github-draft-pr"`
- Branch name `plan-fix-auth-bug-01-15-1430` (draft-PR pattern, no extractable issue number)
- PR body with checkout footer but NO closing reference
- Assert exit code 0, "[PASS] Draft PR plan", "no closing reference needed", "All checks passed"

## Verification

Run `uv run pytest tests/commands/pr/test_check.py` — all existing tests should pass unchanged, new test should pass.

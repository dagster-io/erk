# Remove `--plan` flag from `objective-apply-landed-update`

## Context

The `--pr` and `--plan` flags are redundant because in erk, the PR IS the plan (same GitHub number). Callers pass the same number for both (e.g., `--pr 8884 --plan 8884`). The `--plan` flag should be removed; the command should use `--pr` as the plan number directly.

## Changes

### 1. `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

- **Remove** the `--plan` Click option (lines 149-155) and `plan_number` parameter
- **Remove** the branch-based plan discovery fallback (`get_plan_for_branch`, lines 198-202) — no longer needed
- **After PR is resolved** (either from `--pr` or auto-discovered from branch), use `pr_number` as the plan number:
  ```python
  plan_result = plan_backend.get_plan(repo_root, str(pr_number))
  ```
- Move plan resolution AFTER PR resolution (currently plan resolves before PR; flip the order so we have `pr_number` available)
- Keep `--branch` for PR auto-discovery (`get_pr_for_branch`) and git branch auto-discovery

### 2. `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`

- **Update all test invocations** to remove `--plan` args
- **Update test data** so plan number matches PR number (currently plan=6513, pr=6517 — make them the same, e.g., both 6517)
- **Remove** `test_plan_direct_lookup_skips_branch_discovery` and `test_plan_direct_lookup_not_found` — these test the `--plan` flag specifically
- **Update** `test_bad_branch_no_plan` — this should now test "plan not found for PR number" instead
- Adjust fake setup: plan issue numbers must match PR numbers

### 3. `.claude/commands/erk/system/objective-update-with-landed-pr.md`

- Remove `--plan <number>` from documented flags and example invocations
- Remove the note about `--plan` enabling direct plan lookup

## Verification

- Run `uv run pytest tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
- Run `uv run ruff check src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`
- Run `uv run ty check src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

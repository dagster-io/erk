# Add branch name to workflow run-name for better context

## Context

GitHub Actions workflow run links show a `run-name` like `142:#460:abc456` which gives no context about what the change is about. Daniel requested the workflow link give more context. The `branch_name` input (e.g. `plnd/fix-auth-bug-01-15-1430`) is already available and provides human-readable context.

## Constraint

The `:{distinct_id}` suffix must remain — it's used by `real.py:438` (`f":{distinct_id}" in display_title`) for run correlation. The `#NNN` pattern is used by `extract_pr_number()` in `shared.py`. Both must be preserved.

## Changes

### 1. `.github/workflows/plan-implement.yml` (line 2)

```yaml
# Before: "142:#460:abc456"
# After:  "plnd/fix-auth-bug-01-15-1430 (#460):abc456"
run-name: "${{ inputs.branch_name }} (#${{ inputs.pr_number }}):${{ inputs.distinct_id }}"
```

### 2. Other workflows — leave as-is

- `one-shot.yml` — `branch_name` isn't an input at the top level (generated mid-workflow)
- `pr-address.yml`, `pr-rebase.yml`, `pr-rewrite.yml` — already have descriptive prefixes

### 3. Update `extract_plan_number()` in `src/erk/cli/commands/run/shared.py`

Currently expects `display_title` to start with a plan number (`142:abc456`). With the new format the plan number is no longer at the start. Since plan number equals PR number for planned PRs (both are `plan_id`), and `extract_pr_number()` already extracts `#NNN`, we can either:
- Update `extract_plan_number()` to handle the new format
- Check if any callers depend on it and simplify

### 4. Update tests

- `tests/commands/run/test_list.py` — fixtures with `display_title` matching old format
- `tests/commands/run/test_shared.py` — parser tests

## Verification

- Run unit tests for `run/shared.py` and `run/test_list.py`
- Verify `extract_pr_number()` still finds `#NNN` (it will — regex `#(\d+)`)
- Verify `:{distinct_id}` correlation in `real.py` still works
- Verify `extract_plan_number()` callers handle the change

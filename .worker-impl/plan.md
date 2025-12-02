# Remove -P/--prs Flag from erk dash

## Objective

Remove the `-P/--prs` flag from `erk dash` since the unified GraphQL query now fetches PR linkages alongside issues in a single call with no performance penalty.

## Background

Previously, fetching PR linkages required a separate API call (~1500ms), so the `-P` flag existed to make this optional. With the unified GraphQL query implemented in PR #1887, issues and PR linkages are fetched together (~600ms total), making the flag unnecessary.

## Implementation Steps

### Step 1: Update PlanListService - Remove skip_pr_linkages parameter

**File:** `src/erk/core/services/plan_list_service.py`

- Remove `skip_pr_linkages` parameter from `get_plan_list_data()` signature
- Remove the conditional branch that uses `GitHubIssues.list_issues()` as "light path"
- Always use the unified `get_issues_with_pr_linkages()` path
- Update docstring to remove mention of `skip_pr_linkages`

### Step 2: Update list_cmd.py - Remove -P flag and conditional columns

**File:** `src/erk/cli/commands/plan/list_cmd.py`

- Remove the `--prs/-P` option from `plan_list_options()` decorator
- Remove `prs` parameter from `_build_plans_table()`, `_list_plans_impl()`, and `dash()` functions
- Always add PR columns ("pr", "chks") to the table - remove conditional `if prs:` blocks
- Remove `skip_pr_linkages=not prs` from the service call
- Update `--all/-a` help text from "equivalent to -P -r" to "equivalent to -r" or similar
- Update docstring examples to remove `--prs` examples

### Step 3: Update tests - Remove -P flag usage and skip_pr_linkages

**Files:**
- `tests/unit/services/test_plan_list_service.py` - Remove `skip_pr_linkages=True` from all test calls
- `tests/commands/test_dash.py` - Remove tests that use `--prs` flag, update tests that check for PR columns

### Step 4: Update --all flag behavior

The `--all/-a` flag currently sets both `prs=True` and `runs=True`. After this change:
- Remove `prs = True` assignment (no longer needed)
- Update help text to "Show all columns (equivalent to -r)" or "Show workflow run columns"
- Consider if `-a` should just be an alias for `-r` now, or if it should remain for future extensibility

## Files to Modify

1. `src/erk/core/services/plan_list_service.py` - Remove skip_pr_linkages parameter
2. `src/erk/cli/commands/plan/list_cmd.py` - Remove -P flag and conditional column logic
3. `tests/unit/services/test_plan_list_service.py` - Update test calls
4. `tests/commands/test_dash.py` - Remove --prs tests, update column assertions

## Verification

- Run `make fast-ci` to verify all tests pass
- Run `erk dash` to verify PR columns appear by default
- Run `erk dash -a` to verify behavior unchanged (should show all columns)
- Run `erk dash -r` to verify workflow columns still work
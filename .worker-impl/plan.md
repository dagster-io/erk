# Fix `erk plan list` GraphQL Variable Passing Bug

## Problem

`erk plan list` and `erk dash` fail with:
```
Variable $states of type [IssueState!]! was provided invalid value for 0
(Expected "[\"OPEN\"]" to be one of: OPEN, CLOSED)
Variable $filterBy of type IssueFilters was provided invalid value
```

## Root Cause

In `packages/erk-shared/src/erk_shared/github/real.py`, the `get_issues_with_pr_linkages()` method passes GraphQL array/object variables using `-f` (string flag) instead of `-F` (typed flag).

Per `docs/agent/architecture/github-graphql.md`:
- `-f` = String values
- `-F` = Integer/Boolean/JSON values (performs type conversion)

**Broken code (lines 1032-1042):**
```python
"-f",
f"labels={json.dumps(labels)}",    # ❌ Should be -F
"-f",
f"states={json.dumps(states)}",    # ❌ Should be -F
...
cmd.extend(["-f", f"filterBy={json.dumps({'createdBy': creator})}"])  # ❌ Should be -F
```

## Fix

Change `-f` to `-F` for the `labels`, `states`, and `filterBy` variables:

```python
"-F",
f"labels={json.dumps(labels)}",    # ✅ -F for JSON array
"-F",
f"states={json.dumps(states)}",    # ✅ -F for JSON array
...
cmd.extend(["-F", f"filterBy={json.dumps({'createdBy': creator})}"])  # ✅ -F for JSON object
```

## TDD Approach

The bug is in `RealGitHub` which calls the actual `gh` CLI. True TDD would require an integration test, but the existing fake tests don't exercise the `gh` CLI invocation.

**Strategy**: Write an integration test that validates the actual `gh api graphql` command works:

1. **Write failing integration test** in `tests/integration/test_github_graphql.py`:
   - Call `get_issues_with_pr_linkages()` with real `RealGitHub`
   - Test currently fails due to the bug

2. **Fix the bug** in `real.py`

3. **Verify test passes**

## Files to Modify

1. **Test file (create)**: `tests/integration/test_github_graphql.py`
   - Integration test for `get_issues_with_pr_linkages()`

2. **Fix file**: `packages/erk-shared/src/erk_shared/github/real.py`
   - Lines 1032, 1034: Change `-f` to `-F` for `labels` and `states`
   - Line 1042: Change `-f` to `-F` for `filterBy`

## Related Documentation

- `docs/agent/architecture/github-graphql.md` - GraphQL variable passing patterns
- `fake-driven-testing` skill - Testing strategy for gateway methods
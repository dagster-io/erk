# Remove Dead GraphQL Code

## Summary

Remove three unused GraphQL batch methods and their associated tests. These methods were implemented for batch efficiency but are never called from production code.

## Methods to Remove

| Method | Location | Production Callers |
|--------|----------|-------------------|
| `get_multiple_issue_comments()` | GitHubIssues interface | 0 |
| `enrich_prs_with_ci_status_batch()` | GitHub interface | 0 |
| `fetch_pr_titles_batch()` | GitHub interface | 0 |

## Implementation Steps

### Step 1: Remove `get_multiple_issue_comments()`

**Files to modify:**

1. `packages/erk-shared/src/erk_shared/github/issues/abc.py`
   - Remove abstract method definition (lines 136-155)

2. `packages/erk-shared/src/erk_shared/github/issues/real.py`
   - Remove implementation (lines 188-235)

3. `packages/erk-shared/src/erk_shared/github/issues/fake.py`
   - Remove implementation (lines 204-216)

4. `packages/erk-shared/src/erk_shared/github/issues/dry_run.py`
   - Remove wrapper method (lines 64-68)

**Tests to remove:**

5. `tests/integration/test_real_github_issues.py`
   - Remove 3 tests: `test_get_multiple_issue_comments_*` (lines 813-907)

6. `tests/integration/test_dryrun_integration.py`
   - Remove 1 test: `test_noop_github_issues_get_multiple_issue_comments_delegates` (lines 514-531)

7. `tests/unit/fakes/test_fake_github_issues.py`
   - Remove 5 tests: `test_get_multiple_issue_comments_*` (lines 638-703)

### Step 2: Remove `enrich_prs_with_ci_status_batch()`

**Files to modify:**

1. `packages/erk-shared/src/erk_shared/github/abc.py`
   - Remove abstract method definition (lines 120-135)

2. `packages/erk-shared/src/erk_shared/github/real.py`
   - Remove implementation (lines 368-422)
   - Remove private helper `_build_batch_pr_query()` (lines 219-269)
   - Remove private helper `_extract_aggregated_check_data()` (lines 285-310)
   - Remove private helper `_parse_pr_ci_counts()` (lines 312-325)
   - Remove private helper `_parse_pr_ci_status()` (lines 327-340)
   - Remove private helper `_parse_pr_mergeability()` (lines 342-366)
   - **KEEP** `_execute_batch_pr_query()` - used by other methods

3. `packages/erk-shared/src/erk_shared/github/fake.py`
   - Remove implementation (lines 230-239)

4. `packages/erk-shared/src/erk_shared/github/dry_run.py`
   - Remove wrapper method (lines 70-74)

5. `packages/erk-shared/src/erk_shared/github/printing.py`
   - Remove wrapper method (lines 63-67)

**Tests to remove:**

6. `tests/core/test_github.py`
   - Remove all `test_enrich_prs_with_ci_status_batch_*` tests (lines 42-242)
   - Also remove helper tests: `test_parse_pr_mergeability_*`, `test_build_batch_pr_query_*`

7. `tests/core/operations/test_github.py`
   - Remove helper tests (lines 244-307)

### Step 3: Remove `fetch_pr_titles_batch()`

**Files to modify:**

1. `packages/erk-shared/src/erk_shared/github/abc.py`
   - Remove abstract method definition (lines 102-117)

2. `packages/erk-shared/src/erk_shared/github/real.py`
   - Remove implementation (lines 424-470)
   - Remove private helper `_build_title_batch_query()` (lines 472-498)

3. `packages/erk-shared/src/erk_shared/github/fake.py`
   - Remove implementation (lines 220-228)

4. `packages/erk-shared/src/erk_shared/github/dry_run.py`
   - Remove wrapper method (lines 64-68)

5. `packages/erk-shared/src/erk_shared/github/printing.py`
   - Remove wrapper method (lines 57-61)

**Tests to remove:**

6. `tests/core/operations/test_github.py`
   - Remove 5 tests: `test_fetch_pr_titles_batch_*` and `test_build_title_batch_query_*` (lines 328-525)

7. `tests/unit/fakes/test_fake_github.py`
   - Remove 3 tests: `test_fake_github_fetch_pr_titles_batch_*` (lines 526-595)

### Step 4: Run CI

Run tests and type checking to verify no regressions:
```bash
uv run pytest
uv run pyright
```

## Important Notes

- **DO NOT DELETE** `_execute_batch_pr_query()` - it's used by 5 other methods including `get_prs_linked_to_issues()`, `get_workflow_runs_by_node_ids()`, and `get_issues_with_pr_linkages()`
- Remove methods from ABC first, then implementations, then tests
- Line numbers are approximate - use method names to locate code

## Impact

- ~400 lines of dead code removed
- ~20 test functions removed
- 0 production functionality affected
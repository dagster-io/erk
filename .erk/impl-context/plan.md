# Fix Runs Tab Branch Column

## Context

PR review feedback: The "branch" column in the Runs tab shows "master" for all workflow runs. This happens because `workflow_dispatch` runs use the default branch (master) as their `head_branch` in the GitHub API. The actual target branch is the PR's head branch, not the dispatch ref.

## Root Cause

In `real_provider.py:303`:
```python
branch = run.branch if hasattr(run, "branch") else "-"
```
`run.branch` comes from the GitHub REST API's `head_branch` field, which is always "master" for `workflow_dispatch` events since they're dispatched on the default branch.

## Fix

Use the PR's head branch instead of the workflow run's `head_branch`. Two data paths exist:

1. **Plan-linked runs** (plan-implement): `pr_info_map[pr_num].head_branch` already populated from `get_prs_linked_to_issues` GraphQL query (includes `headRefName`)
2. **Direct-PR runs** (pr-address, pr-rebase): PR number extracted from display_title but no `PullRequestInfo` fetched - need to add fetching

### Approach: Add `get_pr_head_branches` to gateway

Add a batch GraphQL method that fetches `headRefName` for a list of PR numbers in a single API call. This avoids O(n) sequential `get_pr()` calls.

## Files to Modify

### 1. `packages/erk-shared/src/erk_shared/gateway/github/abc.py`
- Add abstract method `get_pr_head_branches(self, location: GitHubRepoLocation, pr_numbers: list[int]) -> dict[int, str]`

### 2. `packages/erk-shared/src/erk_shared/gateway/github/real.py`
- Implement `get_pr_head_branches` with batch GraphQL query:
  ```graphql
  query {
    repository(owner: "...", name: "...") {
      pr_42: pullRequest(number: 42) { headRefName }
      pr_43: pullRequest(number: 43) { headRefName }
    }
  }
  ```
- Use existing `_execute_batch_pr_query` for the API call

### 3. `packages/erk-shared/src/erk_shared/gateway/github/fake.py`
- Implement `get_pr_head_branches` returning from `_prs` (keyed by branch) or `_pr_details` (keyed by PR number, has `head_ref_name`)

### 4. `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`
- Delegate to wrapped implementation (read-only operation)

### 5. `src/erk/tui/data/real_provider.py` (~lines 303)
- After step 4 (batch fetch PR linkages), collect all unique PR numbers from `run_pr_numbers` not in `pr_info_map`
- Call `get_pr_head_branches` for those missing PR numbers
- Build combined branch map from `pr_info_map` head_branches + fetched head_branches
- Replace `run.branch` with `branch_map.get(pr_num, "-")` in row construction

### 6. `tests/tui/data/test_real_provider_runs.py`
- Add test: plan-linked run gets branch from `PullRequestInfo.head_branch`
- Add test: direct-PR run gets branch from `get_pr_head_branches`
- Add test: run with no PR shows "-" for branch

## Verification

1. Run existing tests: `uv run pytest tests/tui/data/test_real_provider_runs.py`
2. Run new tests for branch column
3. Run `erk dash -i`, switch to Runs tab, verify branch column shows actual branch names instead of "master"

# Fix: Objective Nodes Screen Missing PR Data

## Context

The objective nodes screen (`erk dash` → select objective → view nodes) is missing branch, checks, status indicators, and run info for most nodes, even though the same PRs display full data on the main PRs screen. Root causes:

1. **Plans are PRs now, but query still uses `issueOrPullRequest` with Issue/PR union** — The `... on PullRequest` fragment lacks rich fields, and PR linkage parsing only works for Issue-type nodes via `timelineItems`. Since plans ARE PRs, this whole approach should be simplified to query PRs directly.

2. **No workflow runs fetched** — `fetch_plans_by_ids()` always passes `workflow_run=None`.

## Changes

### 1. Rewrite GraphQL query as PR-only

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

Rename `_build_issues_by_numbers_query` → `_build_prs_by_numbers_query`.

Replace `issueOrPullRequest(number: N)` with `pullRequest(number: N)` and include all rich fields directly. Drop the `... on Issue` fragment entirely. Drop the `ISSUE_PR_LINKAGE_FRAGMENT` import (no longer needed in this query). Change alias prefix from `issue_N` to `pr_N`.

```graphql
pr_{num}: pullRequest(number: {num}) {
  number
  title
  body
  state
  url
  author { login }
  labels(first: 100) { nodes { name } }
  assignees(first: 100) { nodes { login } }
  createdAt
  updatedAt
  isDraft
  headRefName
  baseRefName
  statusCheckRollup {
    state
    contexts(last: 1) {
      totalCount
      checkRunCountsByState { state count }
      statusContextCountsByState { state count }
    }
  }
  mergeable
  reviewDecision
  reviewThreads(first: 100) {
    totalCount
    nodes { isResolved }
  }
}
```

### 2. Rewrite response parsing as PR-only

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

Rename `_parse_issues_by_numbers_response` → `_parse_prs_by_numbers_response`.

- Change key prefix check from `issue_` to `pr_`
- Use `_parse_issue_node` to create `IssueInfo` (still needed for `github_issue_to_plan`)
- For every PR node, directly create a `PullRequestInfo` from the rich fields and add to `pr_linkages[number]` as a self-referential entry
- Drop the `timelineItems` parsing entirely (PRs don't have it)

Reuse existing helpers already imported:
- `parse_status_rollup()`, `parse_mergeable_status()`, `parse_review_thread_counts()`

### 3. Update public method and callers

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`
- Update `get_issues_by_numbers_with_pr_linkages` to call renamed private methods

**File:** `packages/erk-shared/src/erk_shared/gateway/github/abc.py`
- Update docstring to reflect PR-only semantics

### 4. Add workflow run fetching to `fetch_plans_by_ids`

**File:** `src/erk/tui/data/real_provider.py`
**Method:** `fetch_plans_by_ids` (~line 211)

After converting issues to plans:
1. Extract dispatch node IDs from issue bodies via `extract_plan_header_dispatch_info()`
2. Batch fetch workflow runs via `self._http_client.graphql()` using `GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY`
3. Pass actual `workflow_run` (instead of `None`) to `_build_row_data()`

New imports needed:
- `from erk_shared.gateway.github.graphql_queries import GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY`
- `from erk_shared.gateway.github.pr_data_parsing import parse_workflow_runs_nodes_response`
- `from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_dispatch_info`

### 5. Update tests

**File:** `tests/unit/gateways/github/test_real.py`
- Update query test to verify `pullRequest(number: N)` with rich fields (not `issueOrPullRequest`)
- Update/replace parse test to verify PR-only parsing creates PullRequestInfo directly

**File:** `tests/tui/data/test_provider.py` — `TestFetchPlansByIds`
- Add test: PR with `pr_linkages` populates `pr_head_branch`, `checks_display`, `status_display`
- Add test: workflow runs fetched when plans have dispatch node IDs

## Verification

1. Run `uv run pytest tests/tui/data/test_provider.py::TestFetchPlansByIds`
2. Run `uv run pytest tests/unit/gateways/github/test_real.py` (for query/parsing tests)
3. Manual: `erk dash -i` → select objective → verify nodes show branch, checks, sts, run-id, run columns

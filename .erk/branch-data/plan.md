# Fix Remaining Missing Data in Draft PR Plans

## Context

The draft-PR plan backend (`DraftPRPlanListService`) shows `-` for most columns in the TUI plan list. Two structural gaps remain after the initial fix (created_at, author, PR linkages, workflow runs):

1. **local-wt**: Always `-` because `_build_worktree_mapping()` uses `extract_leading_issue_number()` which returns `None` for `plan-*` branches
2. **checks + comments**: `list_prs()` REST API returns `PullRequestInfo` with `checks_passing=None`, `checks_counts=None`, `review_thread_counts=None` — shows misleading pending/0/0 instead of real data

Root cause for #2: The issue-based path uses a single GraphQL query (`get_issues_with_pr_linkages`) that returns rich PR data. The draft PR path uses REST `list_prs()` + N x `get_pr()` which returns thin data.

## Changes

### 1. Fix local-wt: plan-ref.json fallback in worktree mapping

**File**: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

Extend `_build_worktree_mapping()` (line 466) to handle `plan-*` branches. When `extract_leading_issue_number()` returns `None` and the branch starts with `plan-`, read `.impl/plan-ref.json` from the worktree path using `read_plan_ref()`.

```python
# After existing extract_leading_issue_number check:
if issue_number is None and worktree.branch and worktree.branch.startswith("plan-"):
    impl_dir = worktree.path / ".impl"
    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is not None and plan_ref.plan_id.isdigit():
        issue_number = int(plan_ref.plan_id)
```

Add import: `from erk_shared.impl_folder import read_plan_ref`

Precedent: `validate_plan_linkage()` in `impl_folder.py:245` uses this exact two-source resolution pattern.

### 2. Add GraphQL query for draft plan PRs

**File**: `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`

Add `GET_PLAN_PRS_WITH_DETAILS_QUERY` — uses `repository().pullRequests()` with labels/states filters and includes the same rich fields as the issue PR linkage query:

- `body` (for plan content extraction)
- `statusCheckRollup` with aggregated counts (for checks column)
- `reviewThreads` with resolved counts (for comments column)
- `mergeable` (for conflict detection)
- `headRefName` (for head_branch)
- `author`, `createdAt`, `updatedAt`, `labels` (for metadata)
- `baseRefName`, `isCrossRepository`, `mergeStateStatus` (for PRDetails)

### 3. Add gateway method (5-place ABC pattern)

New method `list_plan_prs_with_details()` on the GitHub ABC:

```python
def list_plan_prs_with_details(
    self,
    location: GitHubRepoLocation,
    *,
    labels: list[str],
    state: str | None,
    limit: int | None,
    author: str | None,
) -> tuple[list[PRDetails], dict[int, PullRequestInfo]]:
```

Returns `(pr_details_list, pr_linkages)` — parallels the `get_issues_with_pr_linkages()` return pattern.

**Files** (5-place pattern):

| File                 | Action                                                                                                                                                                                             |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `github/abc.py`      | Add abstract method                                                                                                                                                                                |
| `github/real.py`     | Execute GraphQL query, parse response. Reuse `_parse_status_rollup()`, `_parse_mergeable_status()`, `_parse_review_thread_counts()` for parsing. Client-side filter for `draft=True` and `author`. |
| `github/fake.py`     | Return from constructor-injected `_plan_pr_details` / `_plan_pr_linkages` data                                                                                                                     |
| `github/dry_run.py`  | Delegate to wrapped (read-only)                                                                                                                                                                    |
| `github/printing.py` | Delegate to wrapped (read-only)                                                                                                                                                                    |

### 4. Rewrite DraftPRPlanListService to use GraphQL

**File**: `src/erk/core/services/plan_list_service.py`

Replace the current N+1 REST approach:

```python
# OLD: 1 REST list + N REST get_pr
prs = self._github.list_prs(...)
for _branch, pr_info in prs.items():
    pr_details = self._github.get_pr(...)
    ...
    pr_linkages[pr_info.number] = [pr_info]  # thin data
```

With single GraphQL call:

```python
# NEW: 1 GraphQL call returns everything
pr_details_list, pr_linkage_map = self._github.list_plan_prs_with_details(
    location, labels=all_labels, state=state, limit=limit, author=creator
)
for pr_details in pr_details_list:
    plan_body = extract_plan_content(pr_details.body)
    plan = pr_details_to_plan(pr_details, plan_body=plan_body)
    plans.append(plan)
    pr_linkages[pr_details.number] = pr_linkage_map.get(pr_details.number, [])
    # ... workflow run node_id extraction stays the same
```

Performance improvement: 1 API call instead of N+1.

### 5. Tests

**File**: `tests/tui/data/test_provider.py`

- Add test: worktree with `plan-*` branch + `.impl/plan-ref.json` on disk → appears in worktree mapping

**File**: `tests/core/services/test_plan_list_service.py` (or wherever DraftPRPlanListService is tested)

- Update tests for the new GraphQL-based data flow
- Verify PullRequestInfo has rich fields (checks_passing, review_thread_counts)

**File**: `tests/gateway/github/test_fake.py` (or equivalent)

- Add test for new `list_plan_prs_with_details()` fake behavior

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Run `uv run erk dash` with `ERK_PLAN_BACKEND=draft_pr` and verify:
   - `local-wt` shows worktree names for plans with local worktrees
   - `chks` shows actual check status (pass/fail emoji + counts) instead of pending emoji
   - `comments` shows actual review thread counts instead of `0/0`
3. Compare column population between issue-based and draft-PR views — should be equivalent for shared columns

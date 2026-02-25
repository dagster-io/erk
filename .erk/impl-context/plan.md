# Fix: Batch learn issue state fetching in `erk dash`

## Context

Both the **Planned PRs** (tab 1) and **Learn** (tab 2) tabs in `erk dash` are slow to load. Both tabs use `labels=("erk-plan",)` and route through the exact same code path:

```
ErkDashApp._load_data()
  → RealPlanDataProvider.fetch_plans()
    → PlannedPRPlanListService.get_plan_list_data()  [1 GraphQL call - fast]
    → _build_worktree_mapping()                       [local git - fast]
    → _fetch_learn_issue_states()                     [N sequential REST calls - SLOW]
```

The bottleneck is `_fetch_learn_issue_states()` (`real.py:197-217`) which makes **N sequential subprocess+REST calls** — one `gh api repos/{owner}/{repo}/issues/{number}` per learn issue. Each call spawns a `gh` subprocess and does a network round-trip (~250-400ms each). With 10 learn issues, this adds 2.5-4 seconds on top of the ~600ms main GraphQL query.

The codebase already has a batch pattern: `get_workflow_runs_by_node_ids()` uses a single GraphQL `nodes(ids: [...])` query. We should batch learn issue states similarly using a single aliased GraphQL query.

## Approach

Replace the sequential REST loop with a **single dynamically-constructed GraphQL query**:

```graphql
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    issue_123: issue(number: 123) { number state }
    issue_456: issue(number: 456) { number state }
  }
}
```

One API call regardless of N. Needs `{owner}/{repo}` context from the existing `_build_gh_command` plumbing.

## Files to modify

### 1. `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py`
- Add abstract method: `get_issue_states(repo_root, numbers) -> dict[int, str]`

### 2. `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py`
- Implement `get_issue_states()`:
  - Early-return empty dict for empty input
  - Build dynamic GraphQL query with aliases: `issue_{n}: issue(number: {n}) { number state }`
  - Execute single `gh api graphql` call via `execute_gh_command_with_retry`
  - Parse response, mapping issue numbers to state strings ("OPEN" or "CLOSED")
  - Handle missing/null issues gracefully (skip them)

### 3. `packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py`
- Implement `get_issue_states()` using existing fake issue store

### 4. `packages/erk-shared/src/erk_shared/gateway/github/issues/dry_run.py`
- Implement `get_issue_states()` — delegate to inner

### 5. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
- Update `_fetch_learn_issue_states()` (line 197-217):
  - Replace the sequential `for issue_number in issue_numbers: get_issue(...)` loop
  - Call `self._ctx.github.issues.get_issue_states(repo_root, issue_numbers)`
  - Map returned state strings to `is_closed` booleans (`state == "CLOSED"`)

## Verification

1. Run existing tests for plan data provider and issues gateway
2. Run `erk dash` — both Planned PRs and Learn tabs should load noticeably faster
3. Verify learn issue closed/open states still display correctly in the table

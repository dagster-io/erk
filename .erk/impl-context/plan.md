# Plan: Phase 1 — Steelthread: Discriminated Union for GitHub Items

**Part of Objective #9401, Nodes 1.1, 1.2, 1.3**

## Context

The gateway method `get_issues_by_numbers_with_pr_linkages` uses `issueOrPullRequest` GraphQL queries that return mixed Issues and PRs, but the return type is `tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]` — everything gets shoved into `IssueInfo` regardless of whether the underlying GitHub item is an Issue or PR. This creates a "self-linkage" hack where PR nodes create `pr_linkages[pr.number] = [PullRequestInfo(self)]` so that downstream code in `_build_row_data` can extract PR metadata through the same code path used for issues.

This phase introduces `FetchedIssue` and `FetchedPullRequest` as a discriminated union `IssueOrPullRequest`, proving the pattern works end-to-end.

## Implementation

### Step 1: Create FetchedIssue and FetchedPullRequest types (Node 1.1)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/types.py`

Add two new frozen dataclasses and a union type:

```python
@dataclass(frozen=True)
class FetchedIssue:
    """An issue fetched via issueOrPullRequest, with its linked PRs."""
    issue: IssueInfo
    linked_prs: list[PullRequestInfo]

@dataclass(frozen=True)
class FetchedPullRequest:
    """A pull request fetched via issueOrPullRequest, with native PR metadata."""
    issue: IssueInfo  # Base issue fields (number, title, body, etc.)
    pr_info: PullRequestInfo  # Native PR metadata (checks, draft, conflicts)

IssueOrPullRequest = FetchedIssue | FetchedPullRequest
```

Key decisions:
- Both types carry an `IssueInfo` for the base fields (number, title, body, state, etc.) since `_parse_issue_node()` already extracts these uniformly
- `FetchedIssue.linked_prs` replaces the external `pr_linkages` dict for issue-backed items
- `FetchedPullRequest.pr_info` carries the PR metadata natively instead of through self-linkage
- Import `IssueInfo` from `erk_shared.gateway.github.issues.types`

### Step 2: Update `get_issues_by_numbers_with_pr_linkages` signature (Node 1.2)

**4-place update** (gateway uses dry-run pattern):

#### 2a: ABC (`packages/erk-shared/src/erk_shared/gateway/github/abc.py`, ~line 886)

Change return type:
```python
def get_issues_by_numbers_with_pr_linkages(
    self,
    *,
    location: GitHubRepoLocation,
    plan_numbers: list[int],
) -> tuple[list[IssueOrPullRequest], dict[int, list[PullRequestInfo]]]:
```

The return type keeps the tuple structure but changes `list[IssueInfo]` to `list[IssueOrPullRequest]`. The `pr_linkages` dict remains for now (Phase 4 removes self-linkage; this phase just stops adding it for PR nodes).

#### 2b: Real implementation (`packages/erk-shared/src/erk_shared/gateway/github/real.py`, `_parse_issues_by_numbers_response`)

Change the parsing logic:
- For **Issue nodes** (has `timelineItems`): Create `FetchedIssue(issue=issue, linked_prs=parsed_prs)` and still populate `pr_linkages` for backward compat
- For **PR nodes** (has `isDraft`): Create `FetchedPullRequest(issue=issue, pr_info=pr_info)` and still populate `pr_linkages` for backward compat (self-linkage preserved for now — Phase 4 removes it)
- Return `list[IssueOrPullRequest]` instead of `list[IssueInfo]`

#### 2c: Fake (`tests/fakes/gateway/github.py`, ~line 1253)

Update fake to return `list[IssueOrPullRequest]`. The fake currently stores `_issues_data: list[IssueInfo]` — change to `_fetched_items: list[IssueOrPullRequest]` or construct `FetchedIssue` wrappers from the existing `IssueInfo` list.

Approach: Keep accepting `IssueInfo` in the constructor for backward compat, wrap each into `FetchedIssue(issue=info, linked_prs=pr_linkages.get(info.number, []))` on return.

#### 2d: Dry-run (`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`, ~line 399)

Update return type annotation. The dry-run delegates to wrapped impl, so just change the type hint.

### Step 3: Update `fetch_prs_by_ids` consumer (Node 1.3)

**File:** `src/erk/tui/data/real_provider.py` (~line 373)

The main consumer of `get_issues_by_numbers_with_pr_linkages` is `fetch_prs_by_ids`. Currently:
```python
issues, pr_linkages = self._ctx.github.get_issues_by_numbers_with_pr_linkages(...)
plans = [github_issue_to_plan(issue) for issue in issues]
```

Update to handle the union:
```python
fetched_items, pr_linkages = self._ctx.github.get_issues_by_numbers_with_pr_linkages(...)

plans: list[Plan] = []
for item in fetched_items:
    if isinstance(item, FetchedIssue):
        plans.append(github_issue_to_plan(item.issue))
    elif isinstance(item, FetchedPullRequest):
        plans.append(github_issue_to_plan(item.issue))
```

For this phase, both branches call `github_issue_to_plan` on the `.issue` field — the behavior is identical. The discrimination enables Phase 2 to diverge the paths (PR-backed items will use `pr_details_to_planned_pr` instead).

Also update any other consumers that iterate over the returned issues list. Search for all call sites of `get_issues_by_numbers_with_pr_linkages`.

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/types.py` | Add `FetchedIssue`, `FetchedPullRequest`, `IssueOrPullRequest` |
| `packages/erk-shared/src/erk_shared/gateway/github/abc.py` | Update return type |
| `packages/erk-shared/src/erk_shared/gateway/github/real.py` | Update `_parse_issues_by_numbers_response` |
| `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py` | Update return type annotation |
| `tests/fakes/gateway/github.py` | Update fake implementation |
| `src/erk/tui/data/real_provider.py` | Update `fetch_prs_by_ids` to handle union |

## Testing

- Update existing tests that call `get_issues_by_numbers_with_pr_linkages` to expect `FetchedIssue`/`FetchedPullRequest` wrappers
- Add test cases:
  - Issue-only fetch returns `FetchedIssue` with `linked_prs` populated
  - PR-only fetch returns `FetchedPullRequest` with `pr_info` populated
  - Mixed fetch returns both types
  - `fetch_prs_by_ids` works correctly with both types (backward compat)

## Verification

1. Run `make fast-ci` — all unit tests pass
2. Run `ty` — no type errors from the changed signatures
3. Grep for all usages of `get_issues_by_numbers_with_pr_linkages` to ensure no call sites are missed
4. Run `erk dash -i` manually to verify the TUI still displays correctly (if accessible)

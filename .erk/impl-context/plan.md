# Implement PR #7662: Restore Missing PR Status in Draft PR Dashboard

## Context

PR #7662 was created by remote implementation but only the plan files (`.erk/impl-context/`) were committed — no code changes were made. The PR is still in draft state. This plan covers implementing the planned changes and publishing the PR.

When erk switched from issue-based to draft-PR-based plans, the TUI dashboard lost visibility into merge conflict status and review decisions. The `stage` column replaced the `pr` column, but dropped conflict indicators and never had review decision info. This implementation enriches the `stage` column with emoji indicators (e.g., `review 💥`, `review ✔`).

## Workflow

1. Check out PR #7662 branch
2. Implement the changes below
3. Run CI (`make fast-ci`)
4. Publish the PR (mark ready for review)

## Implementation Steps

### Step 1: Add `reviewDecision` to GraphQL queries

**File:** `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`

- **`GET_PLAN_PRS_WITH_DETAILS_QUERY`** (line ~194): Add `reviewDecision` after `mergeStateStatus`
- **`ISSUE_PR_LINKAGE_FRAGMENT`** (line ~74): Add `reviewDecision` after `mergeable`

### Step 2: Add `review_decision` field to `PullRequestInfo`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/types.py`

- Add `review_decision: str | None = None` to `PullRequestInfo` (after `review_thread_counts`, line ~199)
- Values: `"APPROVED"`, `"CHANGES_REQUESTED"`, `"REVIEW_REQUIRED"`, or `None`

### Step 3: Parse `reviewDecision` in GraphQL response parsers

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

- **`_parse_plan_prs_with_details()`** (line ~1700): Extract `node.get("reviewDecision")` and pass to `PullRequestInfo` constructor at line ~1704. Convert empty string to None (GitHub returns `""` for no review decision).
- **`_parse_pr_from_timeline_event()`** (line ~1252): Extract `source.get("reviewDecision")` and pass to `PullRequestInfo` constructor. Note: `ISSUE_PR_LINKAGE_FRAGMENT` needs `reviewDecision` added first (Step 1).

### Step 4: Create `enrich_lifecycle_with_status()` in lifecycle.py

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

New function:

```python
def enrich_lifecycle_with_status(
    lifecycle_display: str,
    *,
    has_conflicts: bool | None,
    review_decision: str | None,
) -> str:
```

Logic:

- Only enrich for stages `implementing` and `review` (check if stage text is present in the display string)
- Build suffix from indicators:
  - `has_conflicts is True` → ` 💥`
  - `review_decision == "APPROVED"` → ` ✔`
  - `review_decision == "CHANGES_REQUESTED"` → ` ❌`
- If no indicators, return unchanged
- Insert suffix before closing Rich markup tag (e.g., `[cyan]review[/cyan]` → `[cyan]review 💥[/cyan]`)
- Handle bare strings (no markup) by appending directly

### Step 5: Wire up in `_build_row_data()`

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

After line 713 (`lifecycle_display = _compute_lifecycle_display(plan)`):

- Track `has_conflicts` and `review_decision` from `selected_pr` (if available, from the PR extraction block at lines 608-635)
- Call `enrich_lifecycle_with_status()` to modify `lifecycle_display`

Approach: Initialize `pr_has_conflicts: bool | None = None` and `pr_review_decision: str | None = None` at the top of the PR section (~line 594). Set them when `selected_pr is not None`. Then after computing `lifecycle_display`, call the enrichment function.

### Step 6: Write tests

**File:** `tests/unit/plan_store/test_lifecycle_display.py`

Add tests for `enrich_lifecycle_with_status()`:

- `review` stage with conflicts → `[cyan]review 💥[/cyan]`
- `review` stage with approved → `[cyan]review ✔[/cyan]`
- `review` stage with changes requested → `[cyan]review ❌[/cyan]`
- `review` stage with conflicts AND changes requested → `[cyan]review 💥 ❌[/cyan]`
- `implementing` stage with conflicts → `[yellow]implementing 💥[/yellow]`
- `planned` stage with conflicts → unchanged (not enriched)
- `merged` stage → unchanged
- No indicators → unchanged
- Bare string (no markup) → appends directly

### Step 7: Update `make_plan_row()` (no changes needed)

`make_plan_row()` already accepts `lifecycle_display` as a string parameter. Since enrichment happens at the string level before constructing `PlanRowData`, the helper doesn't need new parameters. Tests can pass pre-enriched strings like `lifecycle_display="[cyan]review 💥[/cyan]"`.

## Files Modified

| File                                                                         | Change                                           |
| ---------------------------------------------------------------------------- | ------------------------------------------------ |
| `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`       | Add `reviewDecision` to 2 queries                |
| `packages/erk-shared/src/erk_shared/gateway/github/types.py`                 | Add `review_decision` field to `PullRequestInfo` |
| `packages/erk-shared/src/erk_shared/gateway/github/real.py`                  | Parse `reviewDecision` in 2 parser functions     |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` | Add `enrich_lifecycle_with_status()`             |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`      | Wire up enrichment in `_build_row_data()`        |
| `tests/unit/plan_store/test_lifecycle_display.py`                            | Add tests for enrichment function                |

## Verification

1. `make fast-ci` — all tests pass
2. Manually: `erk dash -i` should show enriched stage column (e.g., `review 💥` for PRs with conflicts)
3. Publish the PR via `gh pr ready 7662`

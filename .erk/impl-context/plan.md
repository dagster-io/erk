# Fix misleading data when GraphQL enrichment fails in `erk pr list`

## Context

When `erk pr list` fetches plan data, it uses a two-step approach: REST API fetches issues/PRs, then GraphQL enriches with rich fields (branch names, draft status, checks, etc.). When the GraphQL enrichment fails (e.g., network issue, auth failure), `_enrich_prs_via_graphql` silently returns `{}` (line 1733-1734 in real.py). The downstream `merge_rest_graphql_pr_data` then uses misleading fallback defaults:

- `base_ref_name = ""` → `"" not in ("master", "main")` → **false stacked indicator** (🥞) for ALL plans
- `head_ref_name = ""` → falsy → **branch column shows `-`** instead of actual name
- `is_draft = False` → **false published indicator** (👀) even when draft status is unknown

The user should see an explicit warning that data is degraded, not silently misleading output.

## Approach: All-or-nothing — skip unenriched PR linkages

When `gql` is empty for a PR (no enrichment data), **don't add a `PullRequestInfo` to `pr_linkages`**. This means `_build_row_data` won't enter the `if plan_id in pr_linkages:` block, so all enrichment-dependent fields stay at their default `None`. No type changes needed — existing code already handles the "no PR linkage" case correctly.

## Changes

### 1. Skip unenriched PRs in `pr_linkages` and return count

**File:** `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py`

In `merge_rest_graphql_pr_data`, when `gql` is empty, still create `PRDetails` (needed for plan conversion) but skip the `PullRequestInfo` entry:

```python
def merge_rest_graphql_pr_data(...) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]], int]:
    unenriched_count = 0
    for item in rest_items:
        pr_number = item["number"]
        gql = enrichment.get(pr_number, {})

        # ... create PRDetails as before (always needed for plan conversion) ...

        # Only create PullRequestInfo when enrichment data is available
        if not gql:
            unenriched_count += 1
            continue

        # ... existing PullRequestInfo creation and pr_linkages[pr_number] = [pr_info] ...

    return (pr_details_list, pr_linkages, unenriched_count)
```

### 2. Add `warnings` field to `PlanListData`

**File:** `packages/erk-shared/src/erk_shared/core/plan_list_service.py`

```python
@dataclass(frozen=True)
class PlanListData:
    ...
    warnings: tuple[str, ...] = ()
```

### 3. Detect degradation and populate warnings

**File:** `src/erk/core/services/plan_list_service.py`

In both subprocess and HTTP paths, unpack the 3-tuple and build warnings:

```python
pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data(...)
warnings: list[str] = []
if unenriched_count > 0:
    warnings.append(
        f"GraphQL enrichment failed for {unenriched_count}/{len(pr_details_list)} PRs "
        "— branch, draft status, and check indicators may be missing"
    )
return PlanListData(..., warnings=tuple(warnings))
```

### 4. Add `warnings` to `FetchTimings` and propagate

**File:** `src/erk/tui/data/types.py` — add `warnings: tuple[str, ...] = ()` to `FetchTimings`

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — in `fetch_plans`, set `timings.warnings` from `plan_data.warnings`

### 5. Display warnings in CLI

**File:** `src/erk/cli/commands/pr/list_cmd.py`

After fetching data (line 306), before the table:

```python
rows, timings = provider.fetch_plans(filters)
if timings is not None and timings.warnings:
    for warning in timings.warnings:
        user_output(click.style("Warning: ", fg="yellow") + warning)
```

### 6. Update all `merge_rest_graphql_pr_data` call sites for 3-tuple

Search all callers and unpack the new third element (`unenriched_count`):

- `src/erk/core/services/plan_list_service.py` (both HTTP and subprocess paths)
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` (if called directly)

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py` | Skip unenriched PRs in `pr_linkages`, return `unenriched_count` |
| `packages/erk-shared/src/erk_shared/core/plan_list_service.py` | Add `warnings` to `PlanListData` |
| `src/erk/core/services/plan_list_service.py` | Detect degradation, populate warnings |
| `src/erk/tui/data/types.py` | Add `warnings` to `FetchTimings` |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | Propagate warnings |
| `src/erk/cli/commands/pr/list_cmd.py` | Display warnings before table |

## Test updates

- `tests/core/test_pr_data_parsing.py` — update for 3-tuple return
- Any integration tests calling `merge_rest_graphql_pr_data` — same
- Run `make fast-ci`

## Verification

1. `make fast-ci` (unit tests + type checking)
2. `erk pr list` — verify branch names appear and stacking is correct when enrichment works
3. Simulate enrichment failure — verify warning message and no misleading indicators

# Fix Missing Data in Draft PR Plan Mode

## Context

In draft PR mode, a plan and its PR are one and the same entity — it starts as a draft PR (planning state) and transitions to a real PR (implemented state). There is no separate "issue" and "linked PR"; they're the same GitHub PR at different lifecycle stages.

The erk dash Plans TUI shows incorrect/missing data for plans using the `draft_pr` backend:
- `created` column shows "26y ago" (epoch 2000-01-01 used as sentinel)
- `author` column shows "-" (not extracted from PR data)
- `pr` column shows "-" (pr_linkages always empty — code doesn't know the plan's own PR is its PR)
- `chks`/`comments` show "-" (same root cause as `pr`)

Root causes:
1. `PRDetails` is missing `created_at`, `updated_at`, `author` fields — even though the GitHub REST API returns them in `created_at`, `updated_at`, and `user.login`.
2. `_parse_pr_details_from_rest_api()` doesn't extract these available fields.
3. `pr_details_to_plan()` uses `datetime(2000, 1, 1, tzinfo=UTC)` as a fallback and omits `author` from metadata.
4. `DraftPRPlanListService.get_plan_list_data()` returns `pr_linkages={}` — since the plan IS the PR, `pr_linkages[pr_number] = [pr_info]` should be populated so `_build_row_data()` can display checks and status for the plan's own PR.

## Changes

### 1. Add fields to `PRDetails` — `packages/erk-shared/src/erk_shared/gateway/github/types.py`

Add three new fields with defaults so existing 50+ test files remain unmodified:

```python
from dataclasses import dataclass, field
from datetime import UTC, datetime

@dataclass(frozen=True)
class PRDetails:
    ...
    labels: tuple[str, ...] = ()
    # New fields — default to epoch/empty so existing tests compile without changes
    created_at: datetime = field(default_factory=lambda: datetime(2000, 1, 1, tzinfo=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime(2000, 1, 1, tzinfo=UTC))
    author: str = ""
```

### 2. Extract fields in `_parse_pr_details_from_rest_api()` — `packages/erk-shared/src/erk_shared/gateway/github/real.py`

The REST API always returns these fields. Add extraction before the `return PRDetails(...)`:

```python
# Parse timestamps
created_at_str = data.get("created_at", "")
updated_at_str = data.get("updated_at", "")
created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")) if created_at_str else datetime(2000, 1, 1, tzinfo=UTC)
updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00")) if updated_at_str else datetime(2000, 1, 1, tzinfo=UTC)

# Extract author login
author = data.get("user", {}).get("login", "") if data.get("user") else ""

return PRDetails(
    ...,
    labels=labels,
    created_at=created_at,
    updated_at=updated_at,
    author=author,
)
```

### 3. Use real values in `pr_details_to_plan()` — `packages/erk-shared/src/erk_shared/plan_store/conversion.py`

Remove the epoch sentinel. Use the PR's actual timestamps and include `author` in metadata:

```python
return Plan(
    ...
    created_at=pr.created_at,   # was: epoch
    updated_at=pr.updated_at,   # was: epoch
    metadata={"number": pr.number, "owner": pr.owner, "repo": pr.repo, "author": pr.author},
    ...
)
```

### 4. Populate `pr_linkages` in `DraftPRPlanListService` — `src/erk/core/services/plan_list_service.py`

Build `pr_linkages` from the `PullRequestInfo` objects already fetched via `list_prs()`. In draft PR mode the plan IS the PR, so `pr_linkages[pr_number] = [pr_info]`. This gives `chks` and `comments` columns their data:

```python
pr_linkages: dict[int, list[PullRequestInfo]] = {}
for _branch, pr_info in prs.items():
    pr_details = self._github.get_pr(location.root, pr_info.number)
    if isinstance(pr_details, PRNotFound):
        continue
    plan_body = extract_plan_content(pr_details.body)
    plan = pr_details_to_plan(pr_details, plan_body=plan_body)
    plans.append(plan)
    pr_linkages[pr_info.number] = [pr_info]

    if limit is not None and len(plans) >= limit:
        break

return PlanListData(plans=plans, pr_linkages=pr_linkages, workflow_runs={})
```

Need to add `PullRequestInfo` to the import in `plan_list_service.py`.

### 5. Hide the redundant `pr` column in draft PR mode

The `plan` column already shows the PR number. Showing it again in `pr` is redundant. The existing `show_prs` flag in `PlanFilters` controls `pr` + `chks` + `comments` together — we want to hide only `pr` while keeping `chks` and `comments`. Add a separate flag:

**`src/erk/tui/data/types.py`** — add to `PlanFilters`:
```python
show_pr_column: bool = True  # False in draft_pr mode (plan IS the PR)
```

**`src/erk/tui/widgets/plan_table.py`** — in `_setup_columns()`, split the `pr` column out:
```python
if self._plan_filters.show_prs:
    if self._plan_filters.show_pr_column:
        self._pr_column_index = col_index
        self.add_column("pr", key="pr")
        col_index += 1
    self.add_column("chks", key="chks")
    # ... etc
```

And in `_row_to_values()`, skip the `pr` cell value when `show_pr_column=False`.

**`src/erk/cli/commands/plan/list_cmd.py`** — detect draft PR mode and set the flag:
```python
from erk_shared.plan_store import get_plan_backend

filters = PlanFilters(
    ...
    show_prs=True,  # always show chks/comments
    show_pr_column=get_plan_backend() != "draft_pr",
    ...
)
```

### 6. Update `FakeGitHub.create_pr()` — `packages/erk-shared/src/erk_shared/gateway/github/fake.py`

Set sensible values for the new fields when constructing `PRDetails`:

```python
from datetime import UTC, datetime

details = PRDetails(
    ...,
    labels=(),
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC),
    author=self._repo_info.owner,
)
```

### 7. Update affected test — `tests/unit/services/test_plan_list_service.py`

The test `test_always_returns_empty_pr_linkages_and_workflow_runs` explicitly asserts `result.pr_linkages == {}`. Update it: for a plan with PR number 70, `pr_linkages` should be `{70: [<PullRequestInfo for 70>]}`.

Also add a test verifying that `created_at` and `author` are populated correctly (not epoch).

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/types.py` | Add `created_at`, `updated_at`, `author` to `PRDetails` with defaults |
| `packages/erk-shared/src/erk_shared/gateway/github/real.py` | Extract new fields in `_parse_pr_details_from_rest_api()` |
| `packages/erk-shared/src/erk_shared/plan_store/conversion.py` | Use `pr.created_at`, `pr.updated_at`, `pr.author` in `pr_details_to_plan()` |
| `src/erk/core/services/plan_list_service.py` | Populate `pr_linkages` in `DraftPRPlanListService` |
| `packages/erk-shared/src/erk_shared/gateway/github/fake.py` | Set new fields in `create_pr()` |
| `src/erk/tui/data/types.py` | Add `show_pr_column: bool = True` to `PlanFilters` |
| `src/erk/tui/widgets/plan_table.py` | Split `pr` column rendering from `chks`/`comments` using `show_pr_column` |
| `src/erk/cli/commands/plan/list_cmd.py` | Set `show_pr_column=get_plan_backend() != "draft_pr"` |
| `tests/unit/services/test_plan_list_service.py` | Update `test_always_returns_empty_pr_linkages_and_workflow_runs` |

## Verification

1. Run `make fast-ci` to confirm no regressions
2. Launch `erk dash` and check the Plans tab — `created`, `author`, and `pr` columns should now show real data for draft PR plans
3. Spot-check: the `created` timestamp should match the PR creation date on GitHub

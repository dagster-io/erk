# Plan: Migrate list_cmd.py and plan_data_provider/real.py to PlanBackend

**Part of Objective #7161, Steps 5.1 + 5.2**

## Context

Both `list_cmd.py` (CLI plan list) and `plan_data_provider/real.py` (TUI) bypass PlanBackend in two ways:

1. **Duplicate `_issue_to_plan()` functions** — Both contain identical functions converting `IssueInfo` to `Plan`, duplicating logic already in `GitHubPlanStore._convert_to_plan()`
2. **Direct `extract_plan_header_*()` calls** — Both import 7-12 functions from `plan_header.py` and call them on `plan.body` to extract metadata fields

This migration eliminates both bypasses by:
- Having `PlanListService` return `Plan` objects instead of raw `IssueInfo`
- Enriching `Plan.metadata` with all plan-header fields during conversion
- Consumers read `plan.metadata["field"]` instead of calling `extract_plan_header_*(plan.body)`

This sets up step 5.3 (making `plan_header.py` private to `plan_store/`).

## Architecture

**Current call flow:**
```
Consumer → plan_list_service.get_plan_list_data()
         → PlanListData(issues: list[IssueInfo], pr_linkages, workflow_runs)
         → _issue_to_plan(issue)                    [duplicate local conversion]
         → extract_plan_header_*(plan.body)          [direct plan_header bypass]
```

**After migration:**
```
Consumer → plan_list_service.get_plan_list_data()
         → PlanListData(plans: list[Plan], pr_linkages, workflow_runs)
         → plan.metadata["field_name"]               [pre-parsed during conversion]
```

The `PlanListService` still does its batched GraphQL query (issues + PR linkages in one call). The only change is it converts `IssueInfo` → `Plan` internally before returning.

## Implementation Phases

### Phase 1: Create shared conversion function (new file)

**New file:** `packages/erk-shared/src/erk_shared/plan_store/conversion.py`

Create `issue_info_to_plan(issue: IssueInfo) -> Plan` that:
- Converts `IssueInfo` fields to `Plan` fields (state mapping, etc.)
- Parses ALL plan-header fields from `issue.body` into `Plan.metadata`
- Metadata fields: `number`, `issue_body`, `worktree_name`, `local_impl_at`, `local_impl_event`, `remote_impl_at`, `source_repo`, `review_pr`, `objective_issue`, `learn_status`, `learn_plan_issue`, `learn_plan_pr`, `learn_run_id`, `plan_comment_id`, `last_dispatched_node_id`, `last_dispatched_run_id`

This consolidates:
- `GitHubPlanStore._convert_to_plan()` (line 585 of `plan_store/github.py`)
- `_issue_to_plan()` in `list_cmd.py:52`
- `_issue_to_plan()` in `real.py:760`

### Phase 2: Update GitHubPlanStore to use shared conversion

**File:** `packages/erk-shared/src/erk_shared/plan_store/github.py`

- `_convert_to_plan()` delegates to `issue_info_to_plan()` for the base case
- For `get_plan()`, it then overlays the plan body from comments (existing behavior)
- For `list_plans()`, `issue_info_to_plan()` is used directly (issue body = plan body)

### Phase 3: Change PlanListData to hold Plan objects

**File:** `packages/erk-shared/src/erk_shared/core/plan_list_service.py`

Change `PlanListData`:
```python
# Before
issues: list[IssueInfo]

# After
plans: list[Plan]
```

The `pr_linkages` and `workflow_runs` dicts remain keyed by `int` (issue number). Consumers use `plan.metadata["number"]` as the lookup key (already the existing pattern in both consumers).

### Phase 4: Update RealPlanListService

**File:** `src/erk/core/services/plan_list_service.py`

After the batched GraphQL query returns `(issues, pr_linkages)`:
1. Convert `issues` to `plans` using `issue_info_to_plan()`
2. Extract workflow run node_ids from `plan.metadata["last_dispatched_node_id"]` (instead of from `issue.body`)
3. Return `PlanListData(plans=plans, ...)`

### Phase 5: Update FakePlanListService

**File:** `packages/erk-shared/src/erk_shared/core/fakes.py`

Change default from `PlanListData(issues=[], ...)` to `PlanListData(plans=[], ...)`.

### Phase 6: Migrate list_cmd.py (Step 5.1)

**File:** `src/erk/cli/commands/plan/list_cmd.py`

1. **Remove** `_issue_to_plan()` function (lines 52-76)
2. **Remove** all `extract_plan_header_*` imports (lines 30-38)
3. **Change** `plan_data.issues` → `plan_data.plans` (line 280)
4. **Replace** in `_build_plans_table()` (lines 416-428):
   ```python
   # Before
   extract_plan_header_worktree_name(plan.body)
   extract_plan_header_local_impl_at(plan.body)
   # etc.

   # After
   plan.metadata.get("worktree_name")
   plan.metadata.get("local_impl_at")
   # etc.
   ```
5. **Remove** `IssueInfo` import (no longer needed)

### Phase 7: Migrate plan_data_provider/real.py (Step 5.2)

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

1. **Remove** `_issue_to_plan()` function (lines 760-775)
2. **Remove** plan-header imports used only in `_build_row_data()` and `fetch_plans()`:
   - Remove: `extract_plan_header_local_impl_at`, `extract_plan_header_objective_issue`, `extract_plan_header_remote_impl_at`, `extract_plan_header_review_pr`, `extract_plan_header_worktree_name`, `extract_plan_header_learn_status`, `extract_plan_header_learn_plan_issue`, `extract_plan_header_learn_plan_pr`, `extract_plan_header_learn_run_id`
   - **Keep**: `extract_plan_from_comment`, `extract_plan_header_comment_id` (used in `fetch_plan_content()` which is a separate method, not part of listing)
3. **Change** `plan_data.issues` → `plan_data.plans` in `fetch_plans()` (lines 148-149)
4. **Replace** in `_build_row_data()` (lines 460-475):
   ```python
   # Before
   extracted = extract_plan_header_worktree_name(plan.body)
   local_impl_str = extract_plan_header_local_impl_at(plan.body)

   # After
   extracted = plan.metadata.get("worktree_name")
   local_impl_str = plan.metadata.get("local_impl_at")
   ```
5. **Replace** `extract_plan_header_learn_plan_issue(issue.body)` in the learn-issue batch fetch loop (line 137) with `plan.metadata.get("learn_plan_issue")`

### Phase 8: Update tests

**File:** `tests/commands/plan/test_list.py`
- Update `build_workspace_test_context` calls: tests currently construct `FakeGitHub(issues_data=...)` which feeds `plan_list_service`
- The test helper `plan_to_issue()` stays (still needed to set up FakeGitHub/FakeGitHubIssues)
- If tests use `FakePlanListService` directly, update `PlanListData(issues=...)` → `PlanListData(plans=...)`

**File:** `tests/unit/services/test_plan_list_service.py`
- Update assertions that access `.issues` → `.plans`

**New test:** `tests/unit/plan_store/test_conversion.py`
- Test `issue_info_to_plan()` enriches metadata correctly
- Test with plan-header block containing various fields
- Test with empty body (no plan-header block)

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/conversion.py` | **NEW** — shared `issue_info_to_plan()` |
| `packages/erk-shared/src/erk_shared/plan_store/github.py` | Use shared conversion |
| `packages/erk-shared/src/erk_shared/core/plan_list_service.py` | `PlanListData.issues` → `.plans` |
| `packages/erk-shared/src/erk_shared/core/fakes.py` | Update FakePlanListService |
| `src/erk/core/services/plan_list_service.py` | Convert issues → plans |
| `src/erk/cli/commands/plan/list_cmd.py` | Remove bypasses |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | Remove bypasses |
| `tests/commands/plan/test_list.py` | Update for new data model |
| `tests/unit/services/test_plan_list_service.py` | Update for new data model |
| `tests/unit/plan_store/test_conversion.py` | **NEW** — conversion tests |

## Key Reuse

- `extract_plan_header_*` functions from `plan_header.py` — reused inside `issue_info_to_plan()` (only place they're called for list context)
- `GitHubPlanStore._convert_to_plan()` pattern — basis for `issue_info_to_plan()`
- Existing test patterns in `test_list.py` — `plan_to_issue()` helper, `build_workspace_test_context()`

## What This Does NOT Change

- `PlanBackend.list_plans()` signature stays the same (no `creator` added — that's handled by `plan_list_service` which already supports it)
- `PlanQuery` stays the same
- `FakeLinearPlanBackend` stays the same
- PR linkage and workflow run fetching stays in `plan_list_service` (GitHub-specific enrichment)
- `fetch_plan_content()` in `real.py` still uses `extract_plan_header_comment_id` directly (content fetching, not listing)

## Verification

1. Run `pytest tests/commands/plan/test_list.py` — all 9 existing tests pass
2. Run `pytest tests/unit/services/test_plan_list_service.py` — service tests pass
3. Run `pytest tests/unit/plan_store/test_conversion.py` — new conversion tests pass
4. Run `ruff check` and `ty check` — no lint/type errors
5. Run `erk plan list` manually — output unchanged from before migration
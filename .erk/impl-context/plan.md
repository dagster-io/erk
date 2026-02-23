# Add 🥞 stacked PR emoji to dashboard

## Context

PRs deep in a Graphite stack (base branch != master) can show confusing status in the dashboard — they may appear as draft or conflicting when the real issue is just that they're waiting on parent PRs. The user wants a 🥞 pancake stack emoji to indicate when a PR's immediate parent is not master, making the stacked state visible at a glance.

## Changes

### 1. Add `base_ref_name` field to `PullRequestInfo`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/types.py:201`

Add `base_ref_name: str | None = None` after the existing `review_decision` field. Since it has a default, no existing constructors break.

### 2. Add `baseRefName` to issue PR linkage GraphQL fragment

**File:** `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py:56-78`

Add `baseRefName` to the `ISSUE_PR_LINKAGE_FRAGMENT` `source` fields (it's already in `GET_PLAN_PRS_WITH_DETAILS_QUERY`).

### 3. Populate `base_ref_name` in GraphQL parsers

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

Three locations to update:

- `_parse_pr_from_timeline_event` (~line 1262): Add `base_ref_name=source.get("baseRefName")` to PullRequestInfo constructor
- `_parse_plan_prs_with_details` (~line 1716): Add `base_ref_name=node.get("baseRefName")` to PullRequestInfo constructor
- `list_prs` REST path (~line 1581): Add `base_ref_name=pr_data["base"]["ref"]` to PullRequestInfo constructor

### 4. Add `is_stacked` parameter to indicator functions

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

Add `is_stacked: bool | None = None` keyword parameter to:
- `compute_status_indicators` (line 69)
- `format_lifecycle_with_status` (line 108)
- `_build_indicators` (line 168)

In `_build_indicators`, add 🥞 as the **first** indicator when `is_stacked is True`, before the draft/published indicator. This makes it visible regardless of lifecycle stage.

### 5. Thread `is_stacked` through the data provider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

In `_build_row_data` (~line 596), after extracting `pr_is_draft` from `selected_pr`:
- Extract `base_ref_name = selected_pr.base_ref_name`
- Compute `is_stacked = base_ref_name is not None and base_ref_name not in ("master", "main")`
- Pass `is_stacked=is_stacked` to `compute_status_indicators` call (~line 703)

Also add `"base_ref_name": pr.base_ref_name` to `pr_details_to_plan` metadata in `packages/erk-shared/src/erk_shared/plan_store/conversion.py:101-108` (for completeness, though not strictly needed for the indicator).

### 6. Update tests

**File:** `tests/unit/plan_store/test_lifecycle_display.py`

- Update `_format_lifecycle` and `_indicators` test helpers to accept `is_stacked` parameter (default None)
- Add test: `test_indicators_stacked_shows_pancake` — stacked PR shows 🥞
- Add test: `test_indicators_stacked_with_draft` — stacked + draft shows "🥞 🚧"
- Add test: `test_indicators_stacked_with_conflicts` — stacked + conflicts shows "🥞 💥"
- Add test: `test_indicators_not_stacked_no_pancake` — `is_stacked=False` shows no 🥞
- Add test for `format_lifecycle_with_status` with stacked indicator

## Verification

1. Run scoped tests: `pytest tests/unit/plan_store/test_lifecycle_display.py`
2. Run `erk plan list --limit 10` and confirm PRs stacked on non-master branches show 🥞
3. Verify PRs with base=master do NOT show 🥞

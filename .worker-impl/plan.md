# Plan: Migrate list_cmd.py and RealPlanDataProvider to Pre-Parsed Header Fields

Part of Objective #7161, Steps 5.1 + 5.2

## Context

Both `list_cmd.py` and `real.py` (RealPlanDataProvider) import 7-11 individual `extract_plan_header_*()` functions from `plan_header.py` and call them directly on `plan.body` to extract metadata. Each call re-parses the entire YAML plan-header block. This creates:

1. **Tight coupling** to plan_header internals (blocking Step 5.3: privatize plan_header)
2. **Performance waste**: 6-10 separate YAML parses per plan when one suffices
3. **Code duplication**: identical `_issue_to_plan()` functions in both files

The fix: parse the plan-header block once during IssueInfo-to-Plan conversion, store results in a new `header_fields` dict on the Plan type, and have callers read from that dict using schema constants.

## Changes

### 1. Add `header_fields` to Plan type

**File:** `packages/erk-shared/src/erk_shared/plan_store/types.py`

Add field to the frozen dataclass:
```python
header_fields: dict[str, object] = field(default_factory=dict)
```

Must come after `objective_id` (since it has a default). Using `field(default_factory=dict)` means all ~25 existing Plan construction sites continue to work unchanged.

### 2. Create shared conversion module

**File (new):** `packages/erk-shared/src/erk_shared/plan_store/conversion.py`

Contains:
- `issue_info_to_plan(issue: IssueInfo) -> Plan` — single-parse conversion that populates `header_fields` using `find_metadata_block(issue.body, "plan-header")` and extracts `objective_id` from the parsed dict
- `header_str(header_fields: dict, key: str) -> str | None` — LBYL accessor for string fields, converts `datetime` to ISO string (YAML parser converts ISO timestamps to `datetime` objects, but callers like `format_relative_time()` expect `str | None`)
- `header_int(header_fields: dict, key: str) -> int | None` — LBYL accessor for int fields
- `header_datetime(header_fields: dict, key: str) -> datetime | None` — LBYL accessor for datetime fields (real.py needs both string and datetime representations)

Reuses: `find_metadata_block` from `erk_shared.gateway.github.metadata.core`, `OBJECTIVE_ISSUE` from `schemas.py`

### 3. Migrate list_cmd.py (Step 5.1)

**File:** `src/erk/cli/commands/plan/list_cmd.py`

- **Delete** local `_issue_to_plan()` function (lines 52-76)
- **Delete** all `extract_plan_header_*` imports (lines 30-38)
- **Add** imports: `issue_info_to_plan`, `header_str`, `header_int` from conversion module; schema constants (`WORKTREE_NAME`, `LAST_LOCAL_IMPL_AT`, `LAST_LOCAL_IMPL_EVENT`, `LAST_REMOTE_IMPL_AT`, `SOURCE_REPO`, `REVIEW_PR`)
- **Update** line 280: `plans = [issue_info_to_plan(issue) for issue in plan_data.issues]`
- **Update** `has_cross_repo_plans` check (line 362): read `plan.header_fields.get(SOURCE_REPO)` instead of calling `extract_plan_header_source_repo(plan.body)`
- **Update** field extraction block (lines 416-428): replace 6 extract calls with `header_str()`/`header_int()` lookups using schema constants. Replace `if plan.body:` guard with `if plan.header_fields:`

### 4. Migrate real.py (Step 5.2)

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- **Delete** local `_issue_to_plan()` function (lines 760-775)
- **Remove** 10 `extract_plan_header_*` imports (lines 32-44), **keep** `extract_plan_from_comment` and `extract_plan_header_comment_id`
- **Add** imports: `issue_info_to_plan`, `header_str`, `header_int` from conversion; schema constants (`WORKTREE_NAME`, `LAST_LOCAL_IMPL_AT`, `LAST_REMOTE_IMPL_AT`, `LEARN_STATUS`, `LEARN_PLAN_ISSUE`, `LEARN_PLAN_PR`, `LEARN_RUN_ID`, `REVIEW_PR`, `OBJECTIVE_ISSUE`)
- **Update** `fetch_plans()` line 149: `plan = issue_info_to_plan(issue)`
- **Update** first-pass learn_plan_issue extraction (line 137): convert issues to Plans first, then read `header_int(plan.header_fields, LEARN_PLAN_ISSUE)` from the plans
- **Update** `_build_row_data()` (lines 460-475): replace 8 extract calls with `header_str()`/`header_int()` lookups. For timestamp fields that need both `str | None` and `datetime | None`, use `header_str()` for display and `header_datetime()` for storage
- **Update** `_issue_to_plan(issue)` call at line 774 — now uses shared `issue_info_to_plan`
- **Keep** `extract_plan_header_comment_id` in `fetch_plan_content()` and `extract_plan_from_comment` — these are content retrieval operations (not metadata display), deferring to a future step

### 5. Update GitHubPlanStore._convert_to_plan()

**File:** `packages/erk-shared/src/erk_shared/plan_store/github.py`

- Populate `header_fields` by calling `find_metadata_block(issue_info.body, "plan-header")` (already imported)
- Replace `extract_plan_header_objective_issue(issue_info.body)` call with reading from the parsed header dict
- Remove the `extract_plan_header_objective_issue` import (line 25)
- Keep `metadata["issue_body"]` for now (step 4.6 in current PR #7338 addresses this)

### 6. Update tests

- **New:** `tests/unit/shared/plan_store/test_conversion.py` — test `issue_info_to_plan` with plan-header block, empty body, and missing block; test `header_str`/`header_int`/`header_datetime` helpers
- **Update:** `tests/tui/data/test_provider.py` — Plans in tests are constructed via helpers that set `body=...` with plan-header blocks. After migration, `_build_row_data` reads from `plan.header_fields` instead of `plan.body`, so test Plans need `header_fields` populated. Update `_issue_to_plan` call sites in test helpers to use `issue_info_to_plan`
- **Update:** Any test that constructs `Plan(...)` directly may need `header_fields={}` explicitly only if using positional args (keyword construction with default is fine)

## Key Files

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/types.py` | Add `header_fields` field |
| `packages/erk-shared/src/erk_shared/plan_store/conversion.py` | New: shared conversion + typed accessors |
| `src/erk/cli/commands/plan/list_cmd.py` | Migrate 8 extract calls to header_fields |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | Migrate 10 extract calls to header_fields |
| `packages/erk-shared/src/erk_shared/plan_store/github.py` | Populate header_fields in _convert_to_plan |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` | Read-only: import constants |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` | Read-only: reuse find_metadata_block |
| `tests/unit/shared/plan_store/test_conversion.py` | New: conversion tests |
| `tests/tui/data/test_provider.py` | Update Plan construction |

## Type Handling Note

YAML parsing via `find_metadata_block` converts ISO timestamps to `datetime` objects, but several callers (e.g., `format_relative_time()`, `format_local_run_cell()`) expect `str | None`. The typed accessor helpers (`header_str`, `header_int`, `header_datetime`) handle this cleanly with LBYL `isinstance` checks, matching the pattern established in `view.py` (Phase 4 migration).

## Remaining plan_header imports after this PR

- `real.py`: `extract_plan_from_comment` (comment body parsing — not metadata), `extract_plan_header_comment_id` (content retrieval — deferred)
- `github.py`: `extract_plan_from_comment`, `extract_plan_header_comment_id`, `format_plan_content_comment` (all plan content operations, not metadata)

These are content extraction functions (parsing comment bodies), distinct from metadata field extraction. They'll be addressed when plan content retrieval moves behind PlanBackend.

## Verification

1. Run `make fast-ci` — unit tests, linting, formatting, type checking
2. Run `make all-ci` — integration tests
3. Verify `erk plan list` output matches current behavior
4. Verify `erk dash` TUI displays correctly with plan metadata
5. Confirm no `extract_plan_header_*` imports remain in list_cmd.py
6. Confirm only `extract_plan_from_comment` + `extract_plan_header_comment_id` remain in real.py
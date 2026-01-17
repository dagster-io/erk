# Plan: Add `make_test_plan` Helper and Migrate Tests

## Summary

Create a centralized `make_test_plan()` helper function with sensible defaults and migrate ~26 test files to use it, eliminating repetitive Plan construction boilerplate.

## Problem

Tests create Plan objects with 12 fields, but most only care about 1-3 fields. Current state:
- 26 files with direct Plan instantiations (14+ lines each)
- 4 duplicate helper functions in different conftest files
- 3 duplicate `plan_to_issue()` conversion functions
- Inconsistent patterns across test suites

## Solution

### Phase 1: Create Unified Helper

**File:** `tests/test_utils/plan_helpers.py`

Add `make_test_plan()` with these characteristics:
- `plan_identifier` as only required param (accepts int or str)
- All other fields optional with sensible defaults
- Auto-generates title, url, metadata from plan_identifier
- Defaults: state=OPEN, labels=["erk-plan"], assignees=[], objective_issue=None
- Fixed default timestamp: `datetime(2024, 1, 1, tzinfo=UTC)`

```python
def make_test_plan(
    plan_identifier: str | int,
    *,
    title: str | None = None,  # defaults to "Test Plan {id}"
    body: str = "",
    state: PlanState | None = None,  # defaults to OPEN
    url: str | None = None,  # defaults to github pattern
    labels: list[str] | None = None,  # defaults to ["erk-plan"]
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
    objective_issue: int | None = None,
) -> Plan:
```

### Phase 2: Consolidate `plan_to_issue()`

Move to `tests/test_utils/plan_helpers.py` (already has `_plan_to_issue_info`):
- Export as `plan_to_issue()` (public function)
- Remove duplicates from:
  - `tests/commands/dash/conftest.py`
  - `tests/commands/plan/test_list.py`
  - `tests/commands/test_dash_workflow_runs.py`

### Phase 3: Migrate Tests (by directory)

Use libcst refactor agent for bulk migration where patterns are consistent.

**Priority 1 - Simple migrations (inline Plan → make_test_plan):**
- `tests/commands/plan/test_list.py` (16 instances)
- `tests/commands/plan/test_view.py` (10 instances)
- `tests/commands/plan/test_close.py` (5 instances)
- `tests/commands/plan/test_log.py` (6 instances)
- `tests/commands/dash/test_filtering.py` (11 instances)

**Priority 2 - Moderate migrations:**
- `tests/commands/dash/test_*.py` files (use existing `make_plan` pattern)
- `tests/commands/test_dash_workflow_runs.py` (8 instances)
- `tests/commands/test_top_level_commands.py` (4 instances)

**Priority 3 - Review for consolidation:**
- `tests/commands/submit/conftest.py` - has `create_plan()` helper
- `tests/commands/implement/conftest.py` - has `create_sample_plan_issue()`
- `tests/unit/shared/test_issue_workflow.py` - has `_make_plan()`

### Phase 4: Remove Redundant Helpers

After migration, remove:
- `make_plan()` from `tests/commands/dash/conftest.py`
- `create_plan()` from `tests/commands/submit/conftest.py`
- `_make_plan()` from `tests/unit/shared/test_issue_workflow.py`
- `create_sample_plan_issue()` from `tests/commands/implement/conftest.py`

Keep only `make_test_plan()` and `plan_to_issue()` in `tests/test_utils/plan_helpers.py`.

## Critical Files

**Create/Modify:**
- `tests/test_utils/plan_helpers.py` - Add helper, export plan_to_issue

**Migrate (26 files):**
- `tests/commands/dash/*.py` (7 files)
- `tests/commands/plan/*.py` (4 files)
- `tests/commands/implement/*.py` (2 files)
- `tests/commands/submit/conftest.py`
- `tests/commands/workspace/test_delete.py`
- `tests/commands/test_*.py` (2 files)
- `tests/unit/cli/commands/**/*.py` (3 files)
- `tests/unit/shared/test_issue_workflow.py`
- `tests/tui/data/test_provider.py`

## Before/After Example

**Before (14 lines):**
```python
plan = Plan(
    plan_identifier="42",
    title="Test Issue",
    body="",
    state=PlanState.OPEN,
    url="https://github.com/owner/repo/issues/42",
    labels=["erk-plan"],
    assignees=[],
    created_at=datetime(2024, 1, 1, tzinfo=UTC),
    updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    metadata={},
    objective_issue=None,
)
```

**After (1 line):**
```python
plan = make_test_plan(42, title="Test Issue")
```

## Verification

1. Run `make fast-ci` after each phase
2. Verify no Plan imports remain in migrated test files (except for type hints)
3. Grep for remaining `Plan(` instantiations to catch missed migrations
4. Verify helper functions removed from conftest files
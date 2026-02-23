---
title: Dual Backend Testing
read_when:
  - "writing tests that involve plan storage"
  - "testing plan-related features across both backends"
  - "creating test helpers for plan store operations"
tripwires:
  - action: "writing plan storage tests that parametrize across both backends"
    warning: "After PR #7971 (objective #7911 node 1.1), only the 'draft_pr' backend is active. New plan-related tests should use create_plan_store(backend='draft_pr') directly rather than parametrizing across both backends. The 'github' path is dead code pending removal."
---

# Plan Storage Testing

> **Note:** After PR #7971 (objective #7911 node 1.1), only the `"draft_pr"` backend is active. The `"github"` issue-based backend path is dead code pending removal. This document describes the test infrastructure that still exists for both backends but new tests should use `"draft_pr"` only.

## Test Helpers

All plan test helpers are in `tests/test_utils/plan_helpers.py`.

### `create_plan_store()`

Polymorphic dispatcher (lines 187-207) that accepts a `backend: str` parameter:

- `"github"`: Creates GitHubPlanStore backed by FakeGitHubIssues
- `"draft_pr"`: Creates DraftPRPlanBackend backed by FakeGitHub

Returns `tuple[PlanStore, FakeGitHubIssues | FakeGitHub]` — the store and its backing fake for assertions.

### `create_plan_store_with_plans()`

Creates a GitHubPlanStore pre-populated with plans (lines 65-84). Converts `dict[str, Plan]` to GitHub issue format. Returns `(store, fake_issues)`.

### `_plan_to_pr_details()`

Converts a `Plan` to `PRDetails` for the draft-PR backend (lines 87-133). Handles both:

- Bodies with plan-header metadata block (reformats with separator)
- Plain bodies without metadata (uses directly)

Generates branch names using `f"plan-{plan.plan_identifier}"` and ensures `"erk-plan"` label is present.

### `create_draft_pr_store_with_plans()`

Creates a DraftPRPlanBackend pre-populated with plans (lines 136-184). The draft-PR variant of `create_plan_store_with_plans()`.

## Convention

After PR #7971 (objective #7911 node 1.1), only the `"draft_pr"` backend exists. New plan-related tests should use `create_plan_store(backend="draft_pr")` directly rather than parametrizing across backends. The `"github"` issue-based backend path is dead code pending removal.

## Context Integration

`context_for_test()` in `src/erk/core/context.py` accepts an optional `plan_store` parameter, allowing tests to inject either backend.

## `env_overrides` for Backend Isolation

> **Obsolete:** After PR #7971, the `ERK_PLAN_BACKEND` environment variable no longer affects behavior. The `env_overrides` for this variable are inert. Existing fixtures that set `ERK_PLAN_BACKEND` are exercising dead code paths and will be cleaned up in later nodes of objective #7911.

See [Environment Variable Isolation](environment-variable-isolation.md) for historical context.

## Backend-Conditional Assertion Patterns

> **Note:** The dual-backend parametrize pattern below is now outdated. The `"github"` backend path is dead code. New tests should use `"draft_pr"` only.

```python
# Legacy pattern — do not use for new tests
@pytest.mark.parametrize("backend", ["github", "draft_pr"])
def test_plan_creation(backend: str) -> None:
    store, fake = create_plan_store({}, backend=backend)
    result = store.create_plan(...)

    if backend == "github":
        assert isinstance(fake, FakeGitHubIssues)
        assert len(fake.created_issues) == 1
    else:
        assert isinstance(fake, FakeGitHub)
        assert len(fake.created_prs) == 1
```

For new tests, use `create_plan_store(backend="draft_pr")` directly.

## Related Topics

- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) - Backend architecture
- [Branch Plan Resolution](../planning/branch-plan-resolution.md) - Branch-to-plan resolution
- [Environment Variable Isolation](environment-variable-isolation.md) - ERK_PLAN_BACKEND contamination

---
title: Dual Backend Testing
read_when:
  - "writing tests that involve plan storage"
  - "testing plan-related features across both backends"
  - "creating test helpers for plan store operations"
tripwires:
  - action: "writing plan storage tests without considering both backends"
    warning: "Tests should cover both GitHubPlanStore and DraftPRPlanBackend where applicable. See dual-backend-testing.md."
---

# Dual Backend Testing

Tests must cover both GitHubPlanStore (issue-based) and DraftPRPlanBackend (draft PR-based) plan storage backends.

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

New plan-related tests should parametrize across both backends where the behavior is expected to be consistent. Use `create_plan_store()` with the backend parameter for this.

## Context Integration

`context_for_test()` in `src/erk/core/context.py` accepts an optional `plan_store` parameter, allowing tests to inject either backend.

## `env_overrides` for Backend Isolation

When tests need to run with a specific backend regardless of the environment, use `erk_isolated_fs_env()` from `tests/test_utils/env_helpers.py` to override environment variables. See `tests/unit/cli/commands/test_prepare.py` for representative usage of `env_overrides={"ERK_PLAN_BACKEND": ...}`.

This is especially important when `ERK_PLAN_BACKEND=draft_pr` is set in the developer's shell. See [Environment Variable Isolation](environment-variable-isolation.md) for the full contamination pattern.

## Backend-Conditional Assertion Patterns

Some tests need different assertions depending on the backend:

```python
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

Use `create_plan_store()` from `tests/test_utils/plan_helpers.py` to get the right store-fake pair for each backend.

## Related Topics

- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) - Backend architecture
- [Branch Plan Resolution](../planning/branch-plan-resolution.md) - Branch-to-plan resolution
- [Environment Variable Isolation](environment-variable-isolation.md) - ERK_PLAN_BACKEND contamination

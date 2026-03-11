---
title: Plan Storage Testing
read_when:
  - "writing tests that involve plan storage"
  - "testing plan-related features"
  - "creating test helpers for plan store operations"
tripwires:
  - action: "writing plan storage tests that parametrize across both backends"
    warning: "After PR #8210, only the GitHubManagedPrBackend exists. The GitHubPlanStore class was deleted. New plan-related tests should use GitHubManagedPrBackend directly."
  - action: "using isinstance() to detect plan backend type in application code"
    warning: "Use managed_pr_backend.get_provider_name() for backend-conditional logic (returns 'github-draft-pr'). isinstance checks couple to implementation classes. The provider name string is the stable API."
    score: 7
---

# Plan Storage Testing

> **Note:** After PR #8210, the `GitHubPlanStore` class and `PlanStore` ABC were deleted. Only `GitHubManagedPrBackend` exists. This document describes the test infrastructure for the current single-backend architecture.

## Test Helpers

All plan test helpers are in `tests/test_utils/plan_helpers.py`.

### `create_plan_store_with_plans()`

Creates a `GitHubManagedPrBackend` pre-populated with plans, backed by `FakeGitHub`.

<!-- Source: tests/test_utils/plan_helpers.py, create_plan_store_with_plans -->

See `create_plan_store_with_plans()` in `tests/test_utils/plan_helpers.py` for the full signature. Returns `tuple[GitHubManagedPrBackend, FakeGitHub]` — the backend and its backing fake for assertions.

### `_plan_to_pr_details()`

Converts a `Plan` to `PRDetails` for the planned-PR backend. Handles both:

- Bodies with plan-header metadata block (reformats with separator)
- Plain bodies without metadata (uses directly)

Generates branch names using `f"plan-{plan.plan_identifier}"` and ensures `"erk-pr"` label is present.

## Convention

After PR #8210, only the GitHubManagedPrBackend exists. Use `create_plan_store_with_plans()` for all new tests.

## Context Integration

`context_for_test()` in `src/erk/core/context.py` accepts an optional `plan_store` parameter, allowing tests to inject the backend.

## Assertion Patterns

Tests should use `GitHubManagedPrBackend` directly:

<!-- Source: tests/test_utils/plan_helpers.py, create_plan_store_with_plans -->

See `create_plan_store_with_plans()` in `tests/test_utils/plan_helpers.py` for usage examples. For mutation tracking assertion patterns (e.g., `fake.created_prs`), see [Backend Testing Composition](backend-testing-composition.md).

## Related Topics

- [Planned PR Backend](../planning/planned-pr-backend.md) - Backend architecture
- [Branch Plan Resolution](../planning/branch-plan-resolution.md) - Branch-to-plan resolution

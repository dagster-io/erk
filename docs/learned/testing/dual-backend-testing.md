---
title: Plan Storage Testing
read_when:
  - "writing tests that involve plan storage"
  - "testing plan-related features"
  - "creating test helpers for plan store operations"
tripwires:
  - action: "writing plan storage tests that parametrize across both backends"
    warning: "After PR #8210, only the ManagedGitHubPrBackend exists. The GitHubPlanStore class was deleted. New plan-related tests should use ManagedGitHubPrBackend directly."
  - action: "using isinstance() to detect plan backend type in application code"
    warning: "Use managed_pr_backend.get_provider_name() for backend-conditional logic (returns 'github-draft-pr'). isinstance checks couple to implementation classes. The provider name string is the stable API."
    score: 7
---

# Plan Storage Testing

> **Note:** After PR #8210, the `GitHubPlanStore` class and `PlanStore` ABC were deleted. Only `ManagedGitHubPrBackend` exists. This document describes the test infrastructure for the current single-backend architecture.

## Test Helpers

All plan test helpers are in `tests/test_utils/plan_helpers.py`.

### `create_plan_store_with_plans()`

Creates a `ManagedGitHubPrBackend` pre-populated with plans, backed by `FakeLocalGitHub`.

<!-- Source: tests/test_utils/plan_helpers.py, create_plan_store_with_plans -->

See `create_plan_store_with_plans()` in `tests/test_utils/plan_helpers.py` for the full signature. Returns `tuple[ManagedGitHubPrBackend, FakeLocalGitHub]` — the backend and its backing fake for assertions.

## Convention

After PR #8210, only the ManagedGitHubPrBackend exists. Use `create_plan_store_with_plans()` for all new tests.

## Context Integration

`context_for_test()` in `tests/test_utils/test_context.py` accepts an optional `plan_store` parameter, allowing tests to inject the backend.

## Assertion Patterns

Tests should use `ManagedGitHubPrBackend` directly:

<!-- Source: tests/test_utils/plan_helpers.py, create_plan_store_with_plans -->

See `create_plan_store_with_plans()` in `tests/test_utils/plan_helpers.py` for usage examples. For mutation tracking assertion patterns (e.g., `fake.created_prs`), see [Backend Testing Composition](backend-testing-composition.md).

## Related Topics

- [Planned PR Backend](../planning/planned-pr-backend.md) - Backend architecture
- [Branch Plan Resolution](../planning/branch-plan-resolution.md) - Branch-to-plan resolution

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

## Related Topics

- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) - Backend architecture
- [Branch Plan Resolution](../planning/branch-plan-resolution.md) - Branch-to-plan resolution

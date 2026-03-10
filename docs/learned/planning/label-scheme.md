---
title: PR and Plan Label Assignment Scheme
read_when:
  - "understanding how plans and learn issues are labeled"
  - "working with erk-pr or erk-learn labels"
  - "debugging label filtering in TUI or CLI views"
tripwires:
  - action: "querying core erk PRs using erk-core label"
    warning: "erk-core no longer exists. Use erk-pr with exclude_labels=(erk-learn,) to query non-learn PRs. Use erk-learn only when you need learn-specific filtering."
  - action: "backfilling labels on existing issues without considering updated_at side effects"
    warning: "GitHub label operations change the issue's updated_at timestamp. This affects sort order in list views and may confuse users."
---

# PR and Plan Label Assignment Scheme

Erk uses just **2 labels** for PR classification: `erk-pr` (all erk PRs) and `erk-learn` (learn plans).
Plans are identified by the `[erk-pr]` or `[erk-learn]` title prefix.

## Label Taxonomy

| Label           | Purpose                          | Applied To                           |
| --------------- | -------------------------------- | ------------------------------------ |
| `erk-pr`        | Base label — all erk PRs         | All plans, learn plans, and code PRs |
| `erk-learn`     | Type label — documentation plans | Learn plans                          |
| `erk-objective` | Separate system — objectives     | Objective issues                     |

Title prefix is derived from the plan's labels at creation time. See `packages/erk-shared/src/erk_shared/plan_utils.py`.

## Label Assignment

**Plan PRs** (via `PlannedPRBackend.create_plan()`):

1. Applies `erk-pr` (base label for all erk-submitted PRs)
2. Applies `erk-learn` for learn plans
3. Title is prefixed with `[erk-pr]` or `[erk-learn]` for identification

**Code PRs** (via `erk pr submit` for non-plan branches):

1. The submit pipeline's `label_code_pr` step applies `erk-pr`
2. No title prefix is added (code PRs are not plans)

## Querying by Label

| View             | Query Label     | Exclude Label | Shows             |
| ---------------- | --------------- | ------------- | ----------------- |
| PRs (dash tab 1) | `erk-pr`        | `erk-learn`   | All non-learn PRs |
| Learn            | `erk-learn`     | (none)        | Learn plans only  |
| Objectives       | `erk-objective` | (none)        | Objectives only   |

For plan-only filtering within `erk-pr` results, use client-side `[erk-pr]` title prefix check.

## Client-Side Filtering

The PRs view queries `erk-pr` with `exclude_labels=("erk-learn",)` to show only non-learn PRs.
This client-side exclusion prevents learn PRs from appearing in the main plans tab.

## Label Backfill Side Effects

Adding labels to existing issues changes GitHub's `updated_at` timestamp. This affects:

- Sort order in plan list views (most recently updated first)
- TUI data table ordering
- Any time-based filtering

## Related Documentation

- [TUI View Switching](../tui/view-switching.md) — How views use label-based filtering
- [GitHub GraphQL Label Semantics](../architecture/github-graphql-label-semantics.md) — AND-logic for label filters
- [Glossary: Learn Plan](../glossary.md#learn-plan) — Learn plan definition

---
title: PR and Plan Label Assignment Scheme
read_when:
  - "understanding how plans, code PRs, and learn issues are labeled"
  - "working with erk-pr, erk-plan, or erk-learn labels"
  - "debugging label filtering in TUI or CLI views"
tripwires:
  - action: "querying all erk PRs without using the erk-pr base label"
    warning: "Use erk-pr to query all erk-submitted PRs (plans + code). Use type-specific labels (erk-plan, erk-learn) only when you need to filter to a specific type."
  - action: "backfilling labels on existing issues without considering updated_at side effects"
    warning: "GitHub label operations change the issue's updated_at timestamp. This affects sort order in list views and may confuse users."
---

# PR and Plan Label Assignment Scheme

Erk uses `erk-pr` as the **base label** on all erk-submitted PRs, with **type-specific labels** for filtering plans and learn issues.

## Label Taxonomy

| Label              | Purpose                              | Applied To                                        |
| ------------------ | ------------------------------------ | ------------------------------------------------- |
| `erk-pr`           | Base label — all erk-submitted PRs   | All plans, learn plans, and code PRs              |
| `erk-planned-pr`   | Legacy base label — identifies plans | Historical plans only (no longer applied by code) |
| `erk-plan`         | Type label — implementation plans    | Regular plans                                     |
| `erk-learn`        | Type label — documentation plans     | Learn plans                                       |
| `erk-objective`    | Separate system — objectives         | Objective issues                                  |
| `erk-consolidated` | Consolidation marker                 | Consolidated learn plans                          |

## Label Assignment

**Plan PRs** (via `PlannedPRBackend.create_plan()`):

1. Applies `erk-pr` (base label for all erk-submitted PRs)
2. Applies `erk-plan` for regular plans OR `erk-learn` for learn plans

Note: `erk-planned-pr` exists on older issues but is no longer applied by code.

**Code PRs** (via `erk pr submit` for non-plan branches):

1. The submit pipeline's `label_code_pr` step applies `erk-pr`
2. No type-specific label is added (code PRs are not plans)

## Querying by Label

| View             | Query Label     | Exclude Label | Shows                      |
| ---------------- | --------------- | ------------- | -------------------------- |
| PRs (dash tab 1) | `erk-pr`        | `erk-learn`   | All erk PRs (plans + code) |
| Learn            | `erk-learn`     | (none)        | Learn plans only           |
| Objectives       | `erk-objective` | (none)        | Objectives only            |

For type-specific filtering, use `erk-plan` or `erk-learn` labels directly.

## Defense-in-Depth Filtering

The PRs view uses both server-side and client-side filtering:

1. **Server-side**: Queries with `labels=("erk-pr",)`
2. **Client-side**: `exclude_labels=("erk-learn",)` filters out learn items

This prevents learn plans from appearing in the PRs tab.

## Label Backfill Side Effects

Adding labels to existing issues changes GitHub's `updated_at` timestamp. This affects:

- Sort order in plan list views (most recently updated first)
- TUI data table ordering
- Any time-based filtering

## Related Documentation

- [TUI View Switching](../tui/view-switching.md) — How views use label-based filtering
- [GitHub GraphQL Label Semantics](../architecture/github-graphql-label-semantics.md) — AND-logic for label filters
- [Glossary: Learn Plan](../glossary.md#learn-plan) — Learn plan definition

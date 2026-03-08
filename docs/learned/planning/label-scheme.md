---
title: Erk PR Label Scheme
read_when:
  - "understanding how plans and learn issues are labeled"
  - "working with erk-pr, erk-plan, or erk-learn labels"
  - "debugging label filtering in TUI or CLI views"
tripwires:
  - action: "backfilling labels on existing issues without considering updated_at side effects"
    warning: "GitHub label operations change the issue's updated_at timestamp. This affects sort order in list views and may confuse users."
---

# Erk PR Label Scheme

Erk uses `erk-pr` as the **base label** on ALL erk-submitted PRs — both plan PRs and non-plan code PRs. Type-specific labels provide further classification.

## Label Taxonomy

| Label              | Purpose                            | Applied To                        |
| ------------------ | ---------------------------------- | --------------------------------- |
| `erk-pr`           | Base label — all erk-submitted PRs | Plan PRs, learn PRs, and code PRs |
| `erk-plan`         | Type label — implementation plans  | Regular plans                     |
| `erk-learn`        | Type label — documentation plans   | Learn plans                       |
| `erk-objective`    | Separate system — objectives       | Objective issues                  |
| `erk-consolidated` | Consolidation marker               | Consolidated learn plans          |

## Label Assignment

**Plan PRs**: When `PlannedPRBackend.create_plan()` creates a new issue, it applies `erk-pr` (base) plus `erk-plan` or `erk-learn` (type).

**Code PRs**: The submit pipeline's `label_code_pr` step applies `erk-pr` to non-plan PRs submitted via `erk pr submit`. This ensures all erk-submitted PRs appear in the dashboard.

## Querying by Label

The "PRs" view in the dashboard queries `erk-pr` to show all erk-submitted PRs (plans + code). Type-specific views use type labels:

| View       | Query Label     | Exclude Label |
| ---------- | --------------- | ------------- |
| PRs        | `erk-pr`        | `erk-learn`   |
| Learn      | `erk-learn`     | (none)        |
| Objectives | `erk-objective` | (none)        |

## Defense-in-Depth Filtering

The PRs view uses both server-side and client-side filtering:

1. **Server-side**: Queries with `labels=("erk-pr",)`
2. **Client-side**: `exclude_labels=("erk-learn",)` filters out learn items

This prevents learn plans from appearing in the PRs tab even if they have both labels.

## Label Backfill Side Effects

Adding labels to existing issues changes GitHub's `updated_at` timestamp. This affects:

- Sort order in plan list views (most recently updated first)
- TUI data table ordering
- Any time-based filtering

## Related Documentation

- [TUI View Switching](../tui/view-switching.md) — How views use label-based filtering
- [GitHub GraphQL Label Semantics](../architecture/github-graphql-label-semantics.md) — AND-logic for label filters
- [Glossary: Learn Plan](../glossary.md#learn-plan) — Learn plan definition

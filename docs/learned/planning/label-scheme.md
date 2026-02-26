---
title: Plan Label Assignment Scheme
read_when:
  - "understanding how plans and learn issues are labeled"
  - "working with erk-planned-pr, erk-plan, or erk-learn labels"
  - "debugging label filtering in TUI or CLI views"
tripwires:
  - action: "querying plans using only the erk-planned-pr base label"
    warning: "Use type-specific labels (erk-plan, erk-learn) for queries. The base label erk-planned-pr is for identification, not filtering. See github-graphql-label-semantics.md for AND-logic issues."
  - action: "backfilling labels on existing issues without considering updated_at side effects"
    warning: "GitHub label operations change the issue's updated_at timestamp. This affects sort order in list views and may confuse users."
---

# Plan Label Assignment Scheme

Erk uses a two-label scheme for plan issues: a **base label** for universal identification and a **type-specific label** for filtering and routing.

## Label Taxonomy

| Label              | Purpose                           | Applied To               |
| ------------------ | --------------------------------- | ------------------------ |
| `erk-planned-pr`   | Base label — identifies all plans | All plan/learn issues    |
| `erk-plan`         | Type label — implementation plans | Regular plan issues      |
| `erk-learn`        | Type label — documentation plans  | Learn plan issues        |
| `erk-objective`    | Separate system — objectives      | Objective issues         |
| `erk-consolidated` | Consolidation marker              | Consolidated learn plans |

## Two-Label Assignment

When `PlannedPRBackend.create_plan()` creates a new issue:

1. Always applies `erk-planned-pr` (base label)
2. Applies `erk-plan` for regular plans OR `erk-learn` for learn plans

The type is determined by `plan_type` in the plan metadata.

## Querying by Label

Due to [GitHub GraphQL AND semantics](../architecture/github-graphql-label-semantics.md), always query by **type-specific** labels:

| View       | Query Label     | Exclude Label |
| ---------- | --------------- | ------------- |
| Plans      | `erk-plan`      | `erk-learn`   |
| Learn      | `erk-learn`     | (none)        |
| Objectives | `erk-objective` | (none)        |

Do NOT query by `erk-planned-pr` — it returns all plan types, and combining with a type label triggers AND semantics.

## Defense-in-Depth Filtering

The Plans view uses both server-side and client-side filtering:

1. **Server-side**: Queries with `labels=("erk-plan",)`
2. **Client-side**: `exclude_labels=("erk-learn",)` filters out any learn items

This double filtering prevents learn plans from appearing in the Plans tab even if they have both labels.

## Label Backfill Side Effects

Adding labels to existing issues changes GitHub's `updated_at` timestamp. This affects:

- Sort order in plan list views (most recently updated first)
- TUI data table ordering
- Any time-based filtering

## Related Documentation

- [TUI View Switching](../tui/view-switching.md) — How views use label-based filtering
- [GitHub GraphQL Label Semantics](../architecture/github-graphql-label-semantics.md) — AND-logic for label filters
- [Glossary: Learn Plan](../glossary.md#learn-plan) — Learn plan definition

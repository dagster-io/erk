---
title: GitHub Review Decision Display
read_when:
  - "implementing review decision indicators in the TUI"
  - "understanding how PR review status flows from GraphQL to the TUI display"
  - "debugging missing or incorrect review decision indicators"
---

# GitHub Review Decision Display

The TUI plan list displays review decision status as emoji indicators on plans in the `review` lifecycle stage. This document describes the complete pipeline from GraphQL to display.

## Pipeline

```
GraphQL reviewDecision field
    ↓
PullRequestInfo.review_decision: str | None
    ↓
real.py: selected_pr.review_decision → pr_review_decision
    ↓
compute_status_indicators(review_decision=pr_review_decision)
    ↓
TUI plan list "sts" column with emoji indicators
```

## GraphQL Source

The `reviewDecision` field is fetched in three queries in `graphql_queries.py`:

- Line 76: Single PR detail query
- Line 149: PR list query for plan linkages
- Line 198: PR detail with review info

Raw values returned by GitHub: `"APPROVED"`, `"CHANGES_REQUESTED"`, `"REVIEW_REQUIRED"`, or `null`.

## `PullRequestInfo` Type

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py:201, PullRequestInfo -->

The `review_decision: str | None` field at `packages/erk-shared/src/erk_shared/gateway/github/types.py:201` stores the raw GraphQL `reviewDecision` value.

`None` means the PR has no review state (e.g., no reviewers assigned, or `REVIEW_REQUIRED` maps to no indicator).

## Display Logic

**Location:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py:67-108`

`compute_status_indicators()` produces emoji indicators for the separate "sts" column:

| `review_decision` value | Indicator added |
| ----------------------- | --------------- |
| `"APPROVED"`            | `✔` suffix      |
| `"CHANGES_REQUESTED"`   | `❌` suffix     |
| `"REVIEW_REQUIRED"`     | No indicator    |
| `None`                  | No indicator    |

Review decision indicators only appear on plans in the `review` lifecycle stage. They are suppressed for `planned` and `implementing` stages even if the PR has a review decision.

## Wiring in `real.py`

**Location:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Line 573: `pr_review_decision: str | None = None` — default before PR is found
- Line 599: `pr_review_decision = selected_pr.review_decision` — extracted from matched PR
- Line 715: `review_decision=pr_review_decision` — passed to `compute_status_indicators()`

## Related Documentation

- [Visual Status Indicators](../desktop-dash/visual-status-indicators.md) — Broader status display context
- [Planned PR Lifecycle](../planning/planned-pr-lifecycle.md) — Lifecycle stage definitions

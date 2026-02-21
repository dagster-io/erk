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
format_lifecycle_with_status(review_decision=pr_review_decision)
    ↓
TUI plan list cell with emoji suffix
```

## GraphQL Source

The `reviewDecision` field is fetched in three queries in `graphql_queries.py`:

- Line 75: Single PR detail query
- Line 148: PR list query for plan linkages
- Line 197: PR detail with review info

Raw values returned by GitHub: `"APPROVED"`, `"CHANGES_REQUESTED"`, `"REVIEW_REQUIRED"`, or `null`.

## `PullRequestInfo` Type

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py:201, PullRequestInfo -->

The `review_decision: str | None` field at `packages/erk-shared/src/erk_shared/gateway/github/types.py:201` stores the raw GraphQL `reviewDecision` value.

`None` means the PR has no review state (e.g., no reviewers assigned, or `REVIEW_REQUIRED` maps to no indicator).

## Display Logic

**Location:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py:61-140`

`format_lifecycle_with_status()` adds emoji indicators to the lifecycle stage string:

| `review_decision` value | Indicator added |
| ----------------------- | --------------- |
| `"APPROVED"`            | `✔` suffix     |
| `"CHANGES_REQUESTED"`   | `❌` suffix     |
| `"REVIEW_REQUIRED"`     | No indicator    |
| `None`                  | No indicator    |

Review decision indicators only appear on plans in the `review` lifecycle stage. They are suppressed for `planned` and `implementing` stages even if the PR has a review decision.

## Wiring in `real.py`

**Location:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- Line 612: `pr_review_decision: str | None = None` — default before PR is found
- Line 639: `pr_review_decision = selected_pr.review_decision` — extracted from matched PR
- Line 731: `review_decision=pr_review_decision` — passed to `format_lifecycle_with_status()`

## Related Documentation

- [Visual Status Indicators](../desktop-dash/visual-status-indicators.md) — Broader status display context
- [Draft PR Lifecycle](../planning/draft-pr-lifecycle.md) — Lifecycle stage definitions

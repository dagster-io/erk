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

The `reviewDecision` field is fetched in three queries in `graphql_queries.py` (search for `reviewDecision` to locate):

- `ISSUE_PR_LINKAGE_FRAGMENT` — PR linkage data on cross-referenced events
- `GET_ISSUES_WITH_PR_LINKAGES_QUERY` — issues with PR linkages (nested in PR fragment)
- `GET_PLAN_PRS_WITH_DETAILS_QUERY` — plan PRs with full detail

Raw values returned by GitHub: `"APPROVED"`, `"CHANGES_REQUESTED"`, `"REVIEW_REQUIRED"`, or `null`.

## `PullRequestInfo` Type

<!-- Source: PullRequestInfo class in packages/erk-shared/src/erk_shared/gateway/github/types.py -->

The `review_decision: str | None` field on `PullRequestInfo` in `packages/erk-shared/src/erk_shared/gateway/github/types.py` stores the raw GraphQL `reviewDecision` value.

`None` means the PR has no review state (e.g., no reviewers assigned). This is distinct from `REVIEW_REQUIRED`, which means reviewers are assigned but haven't completed their review. Both produce no indicator in the display, but for different reasons.

## Display Logic

**Location:** `compute_status_indicators()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

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

- `pr_review_decision: str | None = None` — default before PR is found (search for `pr_review_decision` declaration)
- `pr_review_decision = selected_pr.review_decision` — extracted from matched PR (search for `selected_pr.review_decision`)
- `review_decision=pr_review_decision` — passed to `compute_status_indicators()` call

## Related Documentation

- [Planned PR Lifecycle](../planning/planned-pr-lifecycle.md) — Lifecycle stage definitions

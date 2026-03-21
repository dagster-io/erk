---
title: GitHub GraphQL Label Semantics
read_when:
  - "querying GitHub issues or PRs with multiple label filters"
  - "debugging unexpected empty results from GitHub GraphQL label queries"
  - "implementing label-based filtering for plan or issue views"
tripwires:
  - action: "passing multiple labels to a GitHub GraphQL label filter expecting OR semantics"
    warning: "GitHub GraphQL uses AND semantics for label filters. Passing labels=['erk-pr', 'erk-learn'] returns only items with BOTH labels, not either. Query by type-specific labels separately."
  - action: "querying plans by combining multiple type-specific labels in a single query"
    warning: "Query by ONE type-specific label per query (erk-pr, erk-learn). AND semantics means querying labels=['erk-pr', 'erk-learn'] returns only items with BOTH labels, which may silently exclude items."
---

# GitHub GraphQL Label Semantics

GitHub's GraphQL API uses AND semantics for label filter arrays — not OR. This is undocumented and causes silent data loss when queries expect OR behavior.

## The Problem

When you pass `labels: ["erk-pr", "erk-learn"]` to a GitHub GraphQL query, GitHub returns only issues that have **both** labels, not issues with **either** label. This is the opposite of what most developers expect.

## Silent Failure Mode

There is no error, no warning — you simply get fewer results than expected. This makes the bug difficult to detect because:

1. Some items may legitimately have both labels, so results aren't empty
2. The missing items are invisible — you don't know what you're not seeing
3. Tests with small datasets may pass if test items happen to have all labels

## Decision: Query by Type-Specific Labels

Because of AND semantics, erk queries by **type-specific** labels only:

| View       | Query Label     | NOT base label     |
| ---------- | --------------- | ------------------ |
| Plans      | `erk-pr`        | —                  |
| Learn      | `erk-learn`     | —                  |
| Objectives | `erk-objective` | N/A                |

## Impact

This affects all `gh api graphql` calls that include label filters, including:

- TUI view data fetching (Plans, Learn, Objectives tabs)
- CLI plan listing (`erk pr list`)
- Any GraphQL query with the `labels` parameter

## Related Documentation

- [TUI View Switching](../tui/view-switching.md) — How views use label-based filtering
- [GitHub GraphQL API Patterns](github-graphql.md) — General GraphQL patterns

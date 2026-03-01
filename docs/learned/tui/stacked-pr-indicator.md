---
title: Stacked PR Indicator
read_when:
  - "adding or modifying PR indicators in the TUI dashboard"
  - "understanding blocking vs. informational indicators"
  - "working with stacked PR detection"
---

# Stacked PR Indicator

The pancake emoji (🥞) indicates a stacked PR in the TUI dashboard lifecycle column. It appears when a plan's PR targets a branch other than master/main.

## Dual-Source Detection

Stacked status is detected from two sources with a fallback strategy:

1. **Primary: Graphite `get_parent_branch()`** — When the PR head branch is known, the branch manager's `get_parent_branch()` is consulted first. If it returns a parent branch not in `("master", "main")`, the PR is stacked. Graphite is authoritative because it reflects the actual stack topology.

2. **Fallback: GitHub `base_ref_name`** — Only when Graphite returns `None` (branch not tracked locally). The `base_ref_name` field on `PullRequestInfo` is checked against `("master", "main")`.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py:715-725, RealPlanDataProvider._build_row_data -->

See `RealPlanDataProvider._build_row_data()` in `real.py:715-725` for the dual-source detection logic.

## Stale Data Handling

Graphite is authoritative because GitHub's `base_ref_name` can become stale. When a parent PR merges, GitHub does not always update the child PR's target branch immediately — the child may still show the old (now-merged) branch as its base. Graphite's local branch tracking reflects the actual stack state, making it the more reliable source for stacking detection.

## Indicator Ordering

The pancake emoji is the first indicator added in `_build_indicators()`, appearing before CI status, review decision, and merge conflict indicators.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

See `_build_indicators()` in `lifecycle.py` for the full indicator ordering.

## Blocking vs. Informational Classification

Indicators are classified as either **blocking** or **informational**:

- **Blocking indicators** (CI failures, unresolved reviews, merge conflicts) prevent the rocket emoji (🚀) from appearing in the implemented stage.
- **Informational indicators** (🥞 pancake) do not block the rocket.

The mechanism uses a `_non_blocking` set in `_build_indicators()` that defines which indicators are informational. Any indicator not in this set is considered blocking. If a plan is in the `implemented` stage and has no blocking indicators, the rocket emoji is appended.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

See `_build_indicators()` in `lifecycle.py` for the blocking indicator logic.

## Data Flow

```
Graphite get_parent_branch() (local branch tracking, authoritative)
    → pr_is_stacked = parent not in ("master", "main")
    ↓ (if None: Graphite unavailable)
PullRequestInfo.base_ref_name (from GitHub API, fallback)
    → pr_is_stacked = base_ref_name not in ("master", "main")
    ↓
is_stacked parameter (passed to format_lifecycle_with_status / compute_status_indicators)
    → _build_indicators appends 🥞 when is_stacked is True
```

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) — Lifecycle stages and display computation
- [GitHub Interface Patterns](../architecture/github-interface-patterns.md) — PullRequestInfo field addition protocol

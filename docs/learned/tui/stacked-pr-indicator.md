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

1. **Primary: `base_ref_name`** — The `base_ref_name` field on `PullRequestInfo` is checked against `("master", "main")`. If the base ref targets a different branch, the PR is stacked.

2. **Fallback: Graphite `get_parent_branch()`** — If `base_ref_name` detection doesn't confirm stacking and the PR head branch is known, the branch manager's `get_parent_branch()` is consulted. If it returns a parent, the PR is stacked.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, RealPlanDataProvider._build_plan_row -->

See `RealPlanDataProvider._build_plan_row()` in `real.py` for the dual-source detection logic.

## Indicator Ordering

The pancake emoji is the first indicator added in `_build_indicators()`, appearing before CI status, review decision, and merge conflict indicators.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

See `_build_indicators()` in `lifecycle.py` for the full indicator ordering.

## Blocking vs. Informational Classification

Indicators are classified as either **blocking** or **informational**:

- **Blocking indicators** (CI failures, unresolved reviews, merge conflicts) prevent the rocket emoji (🚀) from appearing in the implemented stage.
- **Informational indicators** (🥞 pancake) do not block the rocket.

The mechanism uses an exclusion check:

```
has_blocking_indicators = any(i != "🥞" for i in indicators)
```

If a plan is in the `implemented` stage and has no blocking indicators, the rocket emoji is appended.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

See `_build_indicators()` in `lifecycle.py` for the blocking indicator logic.

## Data Flow

```
PullRequestInfo.base_ref_name (from GitHub API)
    → pr_is_stacked (bool | None, in _build_plan_row)
    → is_stacked parameter (passed to format_lifecycle_with_status / compute_status_indicators)
    → _build_indicators appends 🥞 when is_stacked is True
```

## Related Documentation

- [Visual Status Indicators](../desktop-dash/visual-status-indicators.md) — Color palette and indicator rendering
- [Plan Lifecycle](../planning/lifecycle.md) — Lifecycle stages and display computation
- [GitHub Interface Patterns](../architecture/github-interface-patterns.md) — PullRequestInfo field addition protocol

---
title: TUI Status Indicators
read_when:
  - "working with status indicators in TUI dashboard"
  - "adding new emoji indicators to plan display"
  - "modifying the sts column"
tripwires:
  - action: "adding emoji with Unicode variation selector (\\ufe0f) to status indicators"
    warning: "Variation selector forces double-wide rendering in terminals, breaking column alignment. Current safe emoji: 🥞 🚧 👀 💥 ✔ ❌ 🚀. Test any new emoji in terminal before adding."
    score: 5
  - action: "extracting status indicators from the lifecycle display string"
    warning: "Indicators are computed from RAW PR state fields (is_draft, has_conflicts, review_decision), NOT extracted from lifecycle display. Use compute_status_indicators() for standalone display, format_lifecycle_with_status() for inline."
    score: 4
---

# TUI Status Indicators

Status indicators show PR state as emoji in the TUI dashboard. They are computed from raw PR state fields, not extracted from the lifecycle display string.

## Two Public Functions

**Location:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

### compute_status_indicators() — Standalone Display

Used for the "sts" column in the dashboard. Returns space-joined emoji string or "-" when empty.

```python
compute_status_indicators(
    lifecycle_display="[cyan]impl[/cyan]",
    is_draft=False,
    has_conflicts=False,
    review_decision="APPROVED",
    checks_passing=True,
    has_unresolved_comments=False,
)
# Returns: "👀 🚀"
```

### format_lifecycle_with_status() — Inline Display

Appends indicators inside Rich markup tags so they inherit the stage color. Used when displaying lifecycle and status together in a single column.

```python
format_lifecycle_with_status(
    lifecycle_display="[yellow]impl[/yellow]",
    is_draft=True,
    has_conflicts=True,
    ...
)
# Returns: "[yellow]impl 🚧 💥[/yellow]"
```

## Shared Internal Helper

Both public functions delegate to a shared helper that returns a list of emoji strings.

### Indicator Logic

| Emoji | Meaning           | When Shown                                                               |
| ----- | ----------------- | ------------------------------------------------------------------------ |
| 🥞    | Stacked PR        | Any stage when `is_stacked=True` (base branch != master/main)            |
| 🚧    | Draft PR          | Active stages (planned, implementing, review) when `is_draft=True`       |
| 👀    | Published PR      | Active stages when `is_draft=False`                                      |
| 💥    | Merge conflicts   | Implementing, implemented, or review when `has_conflicts=True`           |
| ✔     | Approved          | Review stage when `review_decision="APPROVED"`                           |
| ❌    | Changes requested | Review stage when `review_decision="CHANGES_REQUESTED"`                  |
| 🚀    | Ready to merge    | Implemented stage when checks pass, no unresolved comments, no conflicts |

### Stage Detection

<!-- Source: _build_indicators() in packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py -->

Stages are detected from the content of `lifecycle_display` using substring matching (not color markup). See `_build_indicators()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` for the current detection logic.

## The "sts" Column

- Width: 4 characters
- Only appears in `draft_pr` view mode
- Displays output of `compute_status_indicators()`

## Related Documentation

- [Column Addition Pattern](column-addition-pattern.md) — How to add new columns to the dashboard
- [TUI Data Contract](data-contract.md) — PlanRowData field conventions

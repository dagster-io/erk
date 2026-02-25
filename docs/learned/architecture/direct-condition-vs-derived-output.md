---
title: Direct Condition vs Derived Output
read_when:
  - "implementing logic that depends on display state"
  - "deciding whether to scan UI output or check raw conditions"
  - "working with indicator or status classification logic"
tripwires:
  - action: "scanning derived display output (emoji lists, formatted strings) to determine state"
    warning: "Check original boolean conditions directly instead. Scanning derived output couples decision logic to display formatting. See direct-condition-vs-derived-output.md."
    score: 6
---

# Direct Condition vs Derived Output

When making decisions based on state, always check the original boolean conditions directly rather than scanning derived display output.

## The Pattern

**Correct: Direct condition checks**

Decision logic evaluates raw state fields independently. Each condition maps to a specific requirement.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

Example from `_build_indicators()` in `lifecycle.py`: the rocket emoji (ready-to-merge) decision checks five raw state fields directly:

- `is_impl` — plan is in implementation stage
- `is_draft is not True` — PR is published
- `has_conflicts is not True` — no merge conflicts
- `review_decision != "CHANGES_REQUESTED"` — no blocking review
- `checks_passing is True` and `has_unresolved_comments is not True` — CI green, threads resolved

**Anti-pattern: Scanning derived output**

Inspecting a rendered emoji list, formatted string, or display column to infer state. This couples the decision to the display format — any change to how indicators are rendered silently breaks the logic.

## Why This Matters

1. **Display formats change independently of state.** Renaming an emoji, reordering indicators, or changing formatting should never break business logic.
2. **Direct checks are exhaustively testable.** Each boolean condition is independently verifiable. Scanning a display string requires integration testing with the full rendering pipeline.
3. **Maintenance clarity.** When a new blocking condition is added, it's obvious where to add it (the condition list). With scanning, you'd need to trace through the rendering to find what new indicator to check for.

## Related Documentation

- [Visual Status Indicators](../desktop-dash/visual-status-indicators.md) — Indicator rendering and color palette
- [Stacked PR Indicator](../tui/stacked-pr-indicator.md) — Informational vs blocking indicator classification

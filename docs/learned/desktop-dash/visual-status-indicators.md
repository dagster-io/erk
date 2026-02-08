---
title: Visual Status Indicators
read_when:
  - implementing visual status indicators in erkdesk
  - adding color-coded status to the erkdesk plan list
  - migrating erkdesk from pre-rendered display strings to derived status
tripwires:
  - action: "Introduce a status color outside the five-color palette"
    warning: "Map to the canonical five colors (green/amber/purple/red/gray) rather than adding new ones. See the color semantics table in this doc."
    score: 7
  - action: "Render status indicators from backend-provided display strings"
    warning: "Status indicators must derive from raw state fields via pure functions, not pre-rendered strings. See state-derivation-pattern.md."
    score: 8
last_audited: "2026-02-08"
audit_result: edited
---

# Visual Status Indicators

## Implementation Status

**Not yet implemented.** An unmerged branch (`P6564-erk-plan-visual-status-in-02-01-1138`) contains a prototype, but the erkdesk plan list still renders pre-rendered display strings (`pr_display`, `checks_display`, `comments_display`) as plain text.

<!-- Source: erkdesk/src/renderer/components/PlanList.tsx -->
<!-- Source: erkdesk/src/types/erkdesk.d.ts, PlanRow -->

See `PlanList` in `erkdesk/src/renderer/components/PlanList.tsx` for current rendering, and `PlanRow` in `erkdesk/src/types/erkdesk.d.ts` for the data contract (which already includes `pr_state` alongside the pre-rendered fields).

## Why Visual Indicators Over Text

Two problems with pre-rendered display strings in a table of 20+ plans:

1. **Scanning friction** — Text like "PR #456 (merged)" requires reading; a colored dot conveys the same at a glance
2. **Inconsistent semantics** — Each display string uses its own formatting. Colored dots enforce a uniform vocabulary across all status columns

## Canonical Color Palette

Any status column in erkdesk should map to these five colors. Do not introduce new colors — map new states to the closest semantic match.

| Color  | Meaning             | Examples                                       |
| ------ | ------------------- | ---------------------------------------------- |
| Green  | Success / Complete  | PR merged, checks passed, all threads resolved |
| Amber  | Warning / Attention | Checks pending, unresolved comments            |
| Purple | In Progress         | Implementation running, plan being executed    |
| Red    | Failure             | PR closed without merge, checks failed         |
| Gray   | Unknown / None      | No data available, status not applicable       |

**Why purple as a fifth color?** Without it, "actively working" and "needs attention" both map to amber. An in-progress plan and a plan with failing comments would look identical, defeating at-a-glance scanning.

## Relationship to State Derivation

Visual indicators are the motivating use case for the [state derivation pattern](../architecture/state-derivation-pattern.md). The key architectural decision: the backend provides raw state fields, and frontend pure functions derive `{color, text, tooltip}` objects.

Three independent derivation functions (PR status, checks status, comments status) keep each function's state space small and exhaustively testable. The rendering component itself has no conditional logic — it receives a color name and renders a CSS dot.

## Migration Path

`PlanRow` already includes `pr_state` alongside the pre-rendered fields, which is the starting point. The pre-rendered fields cannot be removed until the frontend derives all display state from raw fields. See the migration strategy in [state-derivation-pattern.md](../architecture/state-derivation-pattern.md) for the zero-downtime approach (add raw fields first, then switch frontend, then remove pre-rendered fields).

## Related Documentation

- [State Derivation Pattern](../architecture/state-derivation-pattern.md) — The general pattern this feature applies, including migration strategy

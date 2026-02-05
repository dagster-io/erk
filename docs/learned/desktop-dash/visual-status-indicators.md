---
title: Visual Status Indicators
read_when:
  - implementing visual status indicators in erkdesk
  - designing CSS-only status dots with color semantics
  - understanding the backend data contract for status derivation
tripwires:
  - action: "Add new status colors without documenting their semantic meaning"
    warning: "Document color semantics: green=success, amber=warning, purple=in-progress, red=failure, gray=unknown/none."
    score: 6
last_audited: "2026-02-05"
audit_result: edited
---

# Visual Status Indicators

**Status**: Designed but not yet merged. Feature branch `P6564-erk-plan-visual-status-in-02-01-1138` contains the implementation.

## Current State

The erkdesk plan list currently uses pre-rendered display strings from the backend (`pr_display`, `checks_display`, `comments_display`). The visual status indicators feature replaces these with CSS-only colored dots derived from raw state fields through pure functions.

## Color Semantics

| Color  | Meaning             | Use Cases                                      |
| ------ | ------------------- | ---------------------------------------------- |
| Green  | Success             | PR merged, checks passed, all threads resolved |
| Amber  | Warning / Attention | Checks pending, unresolved comments            |
| Purple | In Progress         | Implementation running, plan being executed    |
| Red    | Failure             | PR closed without merge, checks failed         |
| Gray   | Unknown / None      | No data available, status not applicable       |

## Design

The feature uses the [state derivation pattern](../architecture/state-derivation-pattern.md): raw backend fields are transformed into display state through three pure derivation functions (`derivePrStatus`, `deriveChecksStatus`, `deriveCommentsStatus`). See the pattern doc for the general approach and the feature branch for the specific implementation.

## Planned Files

- `erkdesk/src/renderer/components/StatusIndicator.tsx` — CSS dot rendering component
- `erkdesk/src/renderer/components/statusHelpers.ts` — Pure derivation functions
- `erkdesk/src/renderer/components/statusHelpers.test.ts` — Test cases

## Related Documentation

- [State Derivation Pattern](../architecture/state-derivation-pattern.md) — General pattern for raw state to display state

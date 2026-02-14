---
title: State Derivation Pattern
read_when:
  - designing frontend/backend data contracts
  - choosing between pre-rendered strings and raw state fields
  - implementing testable display logic
tripwires:
  - action: "returning pre-rendered display strings from backend APIs"
    warning: "Return raw state fields instead. Derive display state in frontend pure functions for testability and reusability."
    score: 8
last_audited: "2026-02-08"
audit_result: clean
---

# State Derivation Pattern

## Why This Pattern Exists

Backends that return pre-rendered display strings ("PR #456 (merged)", "✓ Passed") create untestable, inflexible frontends. Display logic can't be tested without mocking the entire backend, and UI changes require backend deployments.

**The pattern**: Backends provide raw state fields. Frontends derive display state through pure functions.

This enables exhaustive testing (every state combination), UI flexibility (change colors/text without backend changes), and clear separation of concerns (backend owns data, frontend owns presentation).

## The Core Tradeoff

**Pre-rendered strings**: Easy to implement, impossible to test, couples display to backend
**State derivation**: Requires frontend logic, fully testable, decouples display from backend

Choose state derivation when display logic has multiple variants or changes frequently.

## Pattern Structure

```
Backend (raw fields)  →  Pure Function  →  Display State
     ↓                       ↓                   ↓
pr_state: "closed"    derivePrStatus()    {color: "green",
pr_merged: true       (pure logic)         text: "Merged"}
```

The pure function is the key: no I/O, no side effects, just state transformation. This makes it fully testable.

## Decision: When to Use This Pattern

Use state derivation when:

1. **Display logic varies by context** - Tables show icons, tooltips show text, exports show full descriptions
2. **State combinations are finite** - Can enumerate all cases (3 pr_state values × 2 pr_merged values = 6 cases)
3. **Display requirements change frequently** - Color schemes, wording, formatting change more often than backend data model
4. **Backend has no display context** - Frontend knows user preferences, viewport size, accessibility settings

Skip state derivation when:

1. **Backend performs complex aggregation** - "3 out of 5 subtasks complete" requires backend logic
2. **Derivation requires external context** - Current user permissions, feature flags from backend
3. **Display is inherently backend concern** - Localized timestamps, currency formatting based on user's stored locale

## Anti-Pattern: Pre-Rendered Display Strings

**WRONG**: Backend returns display strings

```typescript
{
  issue_number: 123,
  pr_display: "PR #456 (merged)",     // ❌ Pre-rendered
  status_icon: "✓"                    // ❌ Pre-rendered
}
```

Problems:

- Can't test display logic without mocking backend
- Different UI contexts need different formats (can't reuse)
- Can't change styling without backend deployment
- String parsing required to extract semantic meaning

**CORRECT**: Backend returns raw state, frontend derives display

```typescript
// Backend returns
{ pr_state: "closed", pr_merged: true, pr_number: 456 }

// Frontend derives (pure function)
function derivePrStatus(state, merged, number) {
  if (state === "closed" && merged) {
    return { color: "green", text: "Merged", tooltip: `PR #${number} merged` };
  }
  // ... other cases
}
```

Benefits:

- Test the pure function exhaustively (no mocking)
- Reuse across table cells, tooltips, exports
- Change colors/text without backend deployment
- Type-safe (compile-time checking for missing fields)

## Testing Strategy

Pure derivation functions enable exhaustive state testing:

```typescript
test("merged PR shows green", () => {
  expect(derivePrStatus("closed", true, 456)).toEqual({
    color: "green",
    text: "Merged",
    tooltip: "PR #456 merged",
  });
});

test("closed unmerged PR shows red", () => {
  expect(derivePrStatus("closed", false, 456)).toEqual({
    color: "red",
    text: "Closed",
    tooltip: "PR #456 closed without merge",
  });
});
```

Result: Test every combination of raw state fields. No component mocking, no backend mocking, just input/output pairs.

## Erk Usage

<!-- Source: src/erk/tui/data/types.py, PlanRowData -->

Erk's TUI currently uses pre-rendered display strings (`pr_display`, `checks_display`, `comments_display`) for the plan table. See `PlanRowData` in `src/erk/tui/data/types.py`.

A planned feature (branch `P6564-erk-plan-visual-status-in-02-01-1138`) migrates to state derivation with visual status indicators. The implementation demonstrates this pattern:

- Backend provides raw fields: `pr_state`, `pr_merged`, `run_status`, `run_conclusion`
- Frontend pure functions: `derivePrStatus()`, `deriveChecksStatus()`, `deriveCommentsStatus()`
- Result: 278 tests covering all state combinations

See [visual-status-indicators.md](../desktop-dash/visual-status-indicators.md) for the planned implementation details.

## Migration Strategy

Transitioning from pre-rendered to raw fields without downtime:

1. **Add raw fields** alongside existing pre-rendered fields (backend change)
2. **Deploy backend** with both field types
3. **Update frontend** to use derivation, fallback to old fields if raw fields missing
4. **Deploy frontend** (handles both old and new backend)
5. **Remove pre-rendered fields** from backend after confirming frontend migration
6. **Remove fallback logic** from frontend

This allows zero-downtime rollout. The key is deploying the backend first (additive change), then the frontend (can handle both), then cleanup.

## Pattern Variations

### Multi-Field Derivation

Combine multiple derivation functions for overall status:

```typescript
function deriveOverallStatus(row) {
  const prGreen = derivePrStatus(row).color === "green";
  const checksGreen = deriveChecksStatus(row).color === "green";

  if (prGreen && checksGreen) {
    return { color: "green", text: "All Good" };
  }
  // ... priority order for combined status
}
```

### Conditional Field Presence

Handle optional fields (nullability is part of the state space):

```typescript
function deriveCommentsStatus(resolvedCount, totalCount) {
  if (totalCount === null || totalCount === 0) {
    return { color: "gray", text: "No comments" };
  }

  if ((resolvedCount ?? 0) === totalCount) {
    return { color: "green", text: "All resolved" };
  }

  return { color: "amber", text: `${resolvedCount ?? 0}/${totalCount}` };
}
```

The derivation function explicitly handles the null cases as part of the state space.

## Related Patterns

**Backend for Frontend (BFF)**: State derivation pairs well with BFF. The BFF layer enriches raw database fields with joined/calculated fields (still raw state), then the frontend derives display state.

**Command Query Separation**: State derivation enforces CQS. Commands mutate (create PR, merge PR). Queries return raw state. Display derivation is a pure query with no side effects.

## Historical Context

Erk initially used pre-rendered display strings because they were easier to implement. Testing friction (couldn't test display logic without full backend setup) and inflexibility (every color change required backend deployment) drove the pattern shift.

The planned erkdesk visual status indicators feature is the first systematic application of state derivation in erk.

## Related Documentation

- [visual-status-indicators.md](../desktop-dash/visual-status-indicators.md) — Planned erkdesk implementation with 278 tests

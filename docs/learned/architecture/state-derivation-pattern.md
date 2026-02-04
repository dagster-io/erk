---
title: State Derivation Pattern
read_when:
  - designing frontend/backend data contracts
  - choosing between pre-rendered strings and raw state fields
  - implementing testable display logic
tripwires:
  - action: "Return pre-rendered display strings from backend APIs"
    warning: "Return raw state fields instead. Derive display state in frontend pure functions for testability and reusability."
    score: 8
last_audited: "2026-02-04 14:18 PT"
audit_result: clean
---

# State Derivation Pattern

The state derivation pattern separates raw backend state from display rendering: backends provide raw fields, frontends derive display state through pure functions. This enables exhaustive testing, UI flexibility, and clear separation of concerns.

## Pattern Overview

```
Backend (raw state)  →  Pure Function  →  Display State
   ↓                        ↓                  ↓
pr_state: "closed"    derivePrStatus()    {color: "green",
pr_merged: true       (pure logic)         text: "Merged",
                                           tooltip: "PR #456"}
```

## Anti-Pattern: Pre-Rendered Display Strings

**Wrong approach**: Backend returns display strings

```typescript
// Backend returns
{
  issue_number: 123,
  pr_display: "PR #456 (merged)",     // ❌ Pre-rendered
  status_icon: "✓",                   // ❌ Pre-rendered
  checks_display: "Passed"            // ❌ Pre-rendered
}
```

**Problems:**

1. **Not testable**: Can't test display logic without mocking backend
2. **Not reusable**: Different UI contexts need different formats
3. **Not flexible**: Can't change styling, colors, or tooltips without backend changes
4. **Fragile**: String parsing required to extract semantic meaning

## Correct Pattern: Raw State → Pure Derivation

**Right approach**: Backend returns raw state fields

```typescript
// Backend returns
{
  issue_number: 123,
  pr_state: "closed",      // ✓ Raw field
  pr_merged: true,         // ✓ Raw field
  pr_number: 456           // ✓ Raw field
}

// Frontend derives display state
function derivePrStatus(row: PlanRow): StatusInfo {
  if (row.pr_state === "closed" && row.pr_merged === true) {
    return {
      color: "green",
      text: "Merged",
      tooltip: `PR #${row.pr_number} merged`
    };
  }
  // ... other cases
}
```

**Benefits:**

1. **Fully testable**: Pure function tests without component mocking
2. **Reusable**: Same derivation works across table rows, tooltips, exports
3. **Flexible**: Change colors, text, tooltips without backend changes
4. **Type-safe**: Compile-time checking for missing fields

## Example: erkdesk Status Indicators

### Raw Backend Fields

```typescript
interface PlanRow {
  // PR status fields
  pr_state: "open" | "closed" | null;
  pr_merged: boolean | null;
  pr_number: number | null;

  // Checks status fields
  run_status: string | null; // "completed", "in_progress", etc.
  run_conclusion: string | null; // "success", "failure", etc.

  // Comments status fields
  resolved_comment_count: number | null;
  total_comment_count: number | null;
}
```

### Pure Derivation Function

```typescript
type StatusInfo = {
  color: "green" | "amber" | "purple" | "red" | "gray";
  text: string;
  tooltip: string;
};

function derivePrStatus(row: PlanRow): StatusInfo {
  if (row.pr_state === null) {
    return { color: "gray", text: "No PR", tooltip: "No PR created yet" };
  }

  if (row.pr_state === "closed") {
    if (row.pr_merged === true) {
      return {
        color: "green",
        text: "Merged",
        tooltip: `PR #${row.pr_number} merged`,
      };
    }
    return {
      color: "red",
      text: "Closed",
      tooltip: `PR #${row.pr_number} closed without merge`,
    };
  }

  if (row.pr_state === "open") {
    return {
      color: "purple",
      text: "Open",
      tooltip: `PR #${row.pr_number} is open`,
    };
  }

  return { color: "gray", text: "Unknown", tooltip: "Unknown PR state" };
}
```

### Exhaustive Testing

Pure functions enable testing every state combination:

```typescript
describe("derivePrStatus", () => {
  test("returns green for merged PR", () => {
    const status = derivePrStatus({
      pr_state: "closed",
      pr_merged: true,
      pr_number: 456,
    });
    expect(status.color).toBe("green");
    expect(status.text).toBe("Merged");
  });

  test("returns red for closed unmerged PR", () => {
    const status = derivePrStatus({
      pr_state: "closed",
      pr_merged: false,
      pr_number: 456,
    });
    expect(status.color).toBe("red");
    expect(status.text).toBe("Closed");
  });

  test("returns purple for open PR", () => {
    const status = derivePrStatus({
      pr_state: "open",
      pr_merged: null,
      pr_number: 456,
    });
    expect(status.color).toBe("purple");
  });

  test("returns gray for no PR", () => {
    const status = derivePrStatus({
      pr_state: null,
      pr_merged: null,
      pr_number: null,
    });
    expect(status.color).toBe("gray");
  });
});
```

**Result**: 278 tests covering all state combinations in erkdesk status indicators.

## When to Use This Pattern

Use state derivation when:

1. **Display logic has multiple variants**
   - Different colors, icons, or text based on state
   - Multiple UI contexts (tables, tooltips, cards)

2. **State combinations are finite**
   - Enumerate all cases (3 pr_state × 2 pr_merged = 6 cases)
   - Test every combination exhaustively

3. **Display requirements change frequently**
   - Color schemes, tooltip format, text wording
   - Backend shouldn't deploy for display tweaks

4. **Multiple teams maintain code**
   - Backend team owns data contract
   - Frontend team owns display logic
   - Clear boundary prevents coupling

## When NOT to Use This Pattern

Skip state derivation when:

1. **Backend performs complex aggregation**
   - Example: "3 out of 5 subtasks complete"
   - Aggregation logic belongs in backend

2. **State is inherently a display concern**
   - Example: "formatted_timestamp": "2024-01-15 10:30 PST"
   - This is formatting, not semantic state

3. **Derivation requires external context**
   - Example: Current user's permissions
   - Backend already has this context

## Pattern Variations

### Multi-Field Derivation

Combine multiple raw fields:

```typescript
function deriveOverallStatus(row: PlanRow): StatusInfo {
  const prStatus = derivePrStatus(row);
  const checksStatus = deriveChecksStatus(row);

  if (prStatus.color === "green" && checksStatus.color === "green") {
    return {
      color: "green",
      text: "All Good",
      tooltip: "PR merged, checks passed",
    };
  }
  // ... other combinations
}
```

### Conditional Field Presence

Handle optional fields gracefully:

```typescript
function deriveCommentsStatus(row: PlanRow): StatusInfo {
  if (row.total_comment_count === null || row.total_comment_count === 0) {
    return { color: "gray", text: "No comments", tooltip: "" };
  }

  const resolved = row.resolved_comment_count ?? 0;
  const total = row.total_comment_count;

  if (resolved === total) {
    return {
      color: "green",
      text: "All resolved",
      tooltip: `${total}/${total} resolved`,
    };
  }

  return {
    color: "amber",
    text: "Unresolved",
    tooltip: `${resolved}/${total} resolved`,
  };
}
```

## Related Patterns

### Backend for Frontend (BFF)

State derivation is often paired with BFF pattern:

- **Backend service**: Returns raw database fields
- **BFF layer**: Enriches with additional raw fields (join data, calculated fields)
- **Frontend**: Derives display state from enriched raw fields

### Command Query Separation

State derivation enforces CQS:

- **Commands**: Backend mutations (create PR, merge PR)
- **Queries**: Backend returns raw state
- **Display**: Frontend derivation (no side effects)

## Migration Strategy

Transitioning from pre-rendered to raw fields:

1. **Add raw fields** alongside existing pre-rendered fields
2. **Deploy backend** with both field types
3. **Update frontend** to use derivation functions, fallback to old fields if raw fields missing
4. **Deploy frontend** (handles both old and new backend)
5. **Remove pre-rendered fields** from backend after confirming frontend migration
6. **Remove fallback logic** from frontend

This allows zero-downtime rollout with backward compatibility.

## Related Documentation

- [visual-status-indicators.md](../desktop-dash/visual-status-indicators.md) — erkdesk implementation example with 278 tests

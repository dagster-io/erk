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
---

# Visual Status Indicators

The erkdesk plan list uses CSS-only status indicator dots with a strict color semantic system. Status is derived from raw backend state fields through pure functions, enabling comprehensive testing without component mocking.

## StatusIndicator Component

### CSS-Only Dot Pattern

The `StatusIndicator` component renders a colored dot using pure CSS (no images, no SVG):

```typescript
// Component renders a simple dot with semantic color
<span className={`status-dot status-${color}`} />
```

### Color Semantics

| Color  | Meaning             | Use Cases                                      |
| ------ | ------------------- | ---------------------------------------------- |
| Green  | Success             | PR merged, checks passed, all threads resolved |
| Amber  | Warning / Attention | Checks pending, unresolved comments            |
| Purple | In Progress         | Implementation running, plan being executed    |
| Red    | Failure             | PR closed without merge, checks failed         |
| Gray   | Unknown / None      | No data available, status not applicable       |

**Critical**: These color semantics are consistent across all status indicators (PR status, checks status, comments status).

## State Derivation Pattern

Status is derived from raw backend fields through pure functions, not computed in components or backend.

### Three Derivation Functions

**1. derivePrStatus(planRow): StatusInfo**

Derives PR status from PR state and merged status.

Input fields:

- `pr_state: "open" | "closed" | null`
- `pr_merged: boolean | null`

Output:

- Green: PR merged (`pr_state === "closed" && pr_merged === true`)
- Red: PR closed without merge (`pr_state === "closed" && pr_merged === false`)
- Purple: PR open (`pr_state === "open"`)
- Gray: No PR (`pr_state === null`)

**2. deriveChecksStatus(planRow): StatusInfo**

Derives checks status from run status and conclusion.

Input fields:

- `run_status: string | null` (e.g., "completed", "in_progress")
- `run_conclusion: string | null` (e.g., "success", "failure")

Output:

- Green: Checks passed (`run_status === "completed" && run_conclusion === "success"`)
- Red: Checks failed (`run_status === "completed" && run_conclusion === "failure"`)
- Amber: Checks running (`run_status === "in_progress"`)
- Gray: No checks or unknown state

**3. deriveCommentsStatus(planRow): StatusInfo**

Derives comment resolution status from comment counts.

Input fields:

- `resolved_comment_count: number | null`
- `total_comment_count: number | null`

Output:

- Green: All resolved (`total_comment_count > 0 && resolved_comment_count === total_comment_count`)
- Amber: Partially resolved (`total_comment_count > resolved_comment_count`)
- Gray: No comments (`total_comment_count === 0` or `null`)

### StatusInfo Type

```typescript
type StatusInfo = {
  color: "green" | "amber" | "purple" | "red" | "gray";
  text: string; // Display text (e.g., "Merged", "Checks passed")
  tooltip: string; // Hover tooltip with details
};
```

All three derivation functions return this same structure, enabling consistent rendering across different status types.

## Backend Data Contract

The erkdesk backend provides raw state fields, not pre-rendered display strings.

### Old Contract (Pre-Feature)

Backend returned pre-rendered strings:

```typescript
{
  issue_number: 123,
  pr_display: "PR #456 (merged)",     // Pre-rendered
  checks_display: "✓ Passed",         // Pre-rendered
  comments_display: "3/5 resolved"    // Pre-rendered
}
```

**Problem**: Frontend can't apply custom styling or derive status semantics.

### New Contract (Post-Feature)

Backend returns raw state fields:

```typescript
{
  issue_number: 123,
  pr_state: "closed" | "open" | null,
  pr_merged: boolean | null,
  pr_number: number | null,
  run_status: string | null,
  run_conclusion: string | null,
  resolved_comment_count: number | null,
  total_comment_count: number | null
}
```

**Benefit**: Frontend derives status and styling through pure functions.

## Benefits of Pure Derivation Functions

### 1. Fully Testable Without Component Mocking

Test derivation logic independently of React:

```typescript
test("derivePrStatus returns green for merged PR", () => {
  const planRow = { pr_state: "closed", pr_merged: true };
  const status = derivePrStatus(planRow);
  assert.equal(status.color, "green");
  assert.equal(status.text, "Merged");
});
```

No need for React Testing Library or component mounting.

### 2. Reusable Across UI Contexts

Same derivation function works in:

- Table rows (main plan list)
- Detail panels (expanded view)
- Tooltips (hover previews)
- Export formats (CSV, JSON)

### 3. Exhaustive Testing (278 Tests)

Pure functions enable testing every state combination:

```typescript
// Test all PR state combinations (3 pr_state × 3 pr_merged = 9 cases)
// Test all checks combinations (5 run_status × 6 run_conclusion = 30 cases)
// Test all comment combinations (10 resolved_count × 10 total_count = 100 cases)
// Total: 278 test cases covering edge cases
```

Component-based derivation would make this testing infeasible.

### 4. Transparent Logic

The derivation is self-documenting:

```typescript
if (pr_state === "closed" && pr_merged === true) {
  return { color: "green", text: "Merged", tooltip: `PR #${pr_number} merged` };
}
```

No hidden logic in backend or component lifecycle.

## Implementation Location

**Feature branch**: `P6564-erk-plan-visual-status-in-02-01-1138`

**Key files**:

- `erkdesk/src/renderer/components/StatusIndicator.tsx` — Component (CSS dot rendering)
- `erkdesk/src/renderer/components/statusHelpers.ts` — Derivation functions
- `erkdesk/src/renderer/components/statusHelpers.test.ts` — 278 test cases

## Related Patterns

This is an instance of the [state-derivation-pattern.md](../architecture/state-derivation-pattern.md): raw backend fields → pure function → display state.

Other examples in erk:

- Objective progress derivation (turns count → percentage)
- Plan staleness detection (created_at → days_old → amber/red)
- Session health status (token_count → utilization → warning levels)

## Migration Strategy

When transitioning from pre-rendered to raw fields:

1. **Add new raw fields** to backend response (keep old pre-rendered fields temporarily)
2. **Implement derivation functions** in frontend with comprehensive tests
3. **Update components** to use derivation functions, fallback to old fields if new fields missing
4. **Deploy frontend** (handles both old and new backend)
5. **Deploy backend** with new raw fields
6. **Remove old pre-rendered fields** after confirming frontend migration

This zero-downtime migration prevents frontend breakage during rollout.

## Related Documentation

- [state-derivation-pattern.md](../architecture/state-derivation-pattern.md) — General pattern for raw state → display state

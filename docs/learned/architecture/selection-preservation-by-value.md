---
title: Selection Preservation by Value
read_when:
  - "working with auto-refreshing lists or tables in UI components"
  - "implementing selection state that should persist across data updates"
  - "building real-time dashboard views with user-selected items"
  - "debugging cursor position resets in DataTable or list components"
category: architecture
tripwires:
  - action: "tracking selection by array index when the array can be mutated"
    warning: "Track selection by unique identifier (issue_number, row key), not array position. Array indices become unstable when rows are added, removed, or reordered."
  - action: "assuming cursor position will persist across DataTable.clear() calls"
    warning: "Save cursor position by row key before clear(), restore after repopulating. See textual/quirks.md for pattern."
  - action: "skipping fallback strategies when the selected item might disappear"
    warning: "Always provide fallback behavior when selected item not found in refreshed data (reset to 0, preserve index clamped, or clear selection)."
---

# Selection Preservation by Value

## Problem

When displaying dynamic lists that refresh periodically, array indices become unstable:

- New rows may be inserted at any position
- Rows may be removed (plans completed, tasks cancelled)
- Rows may reorder (sorting, priority changes)

Tracking selection by array position causes the user to "lose their place" when data refreshes - the cursor jumps to a different item, or resets to the first row.

## Solution Pattern

**Track selection by unique identifier**, not array position. After refreshing data:

1. Look up the previously selected item by its ID in the new data
2. If found, move the cursor to its new position
3. If not found (item disappeared), use a fallback strategy

## React Implementation

**Example:** `erkdesk/src/renderer/App.tsx` lines 36-43

```typescript
setSelectedIndex((prevIndex) => {
  const previousIssueNumber = prevPlans[prevIndex]?.issue_number;
  if (previousIssueNumber === undefined) return 0;
  const newIndex = newPlans.findIndex(
    (p) => p.issue_number === previousIssueNumber,
  );
  return newIndex >= 0 ? newIndex : 0;
});
```

**Key elements:**

- Save `issue_number` from the currently selected item
- Use `findIndex()` to locate it in the refreshed data
- Fall back to index 0 if the item disappeared

**Why this works:**

- `issue_number` is stable (GitHub assigns once, never changes)
- `findIndex()` handles reordering transparently
- Fallback ensures valid state even when items disappear

## Python/Textual Implementation

**Example:** `src/erk/tui/widgets/plan_table.py` lines 158-185

See `PlanTable.populate()` in `src/erk/tui/widgets/plan_table.py:158` for the full implementation.

**Key elements:**

- Save `selected_key` (stringified `issue_number`) before clearing
- Also save `saved_cursor_row` as a fallback
- Loop through new data to find matching `issue_number`
- If found, move cursor to that row
- If not found, clamp saved index to valid range

**Why this approach:**

- Two-tier fallback: prefer value-based, accept position-based
- LBYL bounds checking prevents invalid cursor positions
- Works correctly even when multiple rows are added/removed/reordered

## Fallback Strategies

Different UX goals require different fallback behaviors:

| Strategy        | When to Use                       | React Example                          | Python Example                         |
| --------------- | --------------------------------- | -------------------------------------- | -------------------------------------- |
| Reset to 0      | User should see the top item      | `return 0`                             | `self.move_cursor(row=0)`              |
| Preserve index  | User should see nearby items      | `return min(prevIndex, newLength - 1)` | `min(saved_cursor_row, len(rows) - 1)` |
| Clear selection | Selection is invalid if item gone | `return null`                          | `self.cursor_row = None`               |

**Erk convention:**

- **erkdesk (Electron):** Reset to 0 (user expects to see latest plans)
- **erk TUI:** Preserve index, clamped (user is navigating a stable list)

## Cross-References

- [Textual Quirks: clear() Resets Cursor Position](../textual/quirks.md#clear-resets-cursor-position) - Detailed Textual-specific behavior
- [Erkdesk Auto-Refresh Patterns](../desktop-dash/erkdesk-auto-refresh-patterns.md) - Full refresh cycle including this pattern

## Related Patterns

- **React setState with function:** `setSelectedIndex((prev) => ...)` ensures you read the latest state
- **DataTable row keys:** Always provide `key=` when calling `add_row()` for stable identifiers
- **LBYL bounds checking:** Always verify `cursor_row` is within valid range before accessing `_rows[cursor_row]`

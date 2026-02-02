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

```python
def populate(self, rows: list[PlanRowData]) -> None:
    """Populate table with plan data, preserving cursor position."""
    # Save current selection by issue number (row key)
    selected_key: str | None = None
    if self._rows and self.cursor_row is not None and 0 <= self.cursor_row < len(self._rows):
        selected_key = str(self._rows[self.cursor_row].issue_number)

    # Save cursor row index for fallback
    saved_cursor_row = self.cursor_row

    self._rows = rows
    self.clear()

    for row in rows:
        values = self._row_to_values(row)
        self.add_row(*values, key=str(row.issue_number))

    # Restore cursor position
    if rows:
        # Try to restore by key (issue number) first
        if selected_key is not None:
            for idx, row in enumerate(rows):
                if str(row.issue_number) == selected_key:
                    self.move_cursor(row=idx)
                    return

        # Plan disappeared - stay at same row index, clamped to valid range
        if saved_cursor_row is not None and saved_cursor_row >= 0:
            target_row = min(saved_cursor_row, len(rows) - 1)
            self.move_cursor(row=target_row)
```

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

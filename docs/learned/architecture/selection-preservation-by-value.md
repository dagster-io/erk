---
title: Selection Preservation by Value
read_when:
  - "working with auto-refreshing lists or tables in UI components"
  - "implementing selection state that should persist across data updates"
  - "building real-time dashboard views with user-selected items"
  - "debugging cursor position resets in DataTable or list components"
last_audited: "2026-02-07 21:34 PT"
audit_result: edited
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

## The Problem

Array indices are fundamentally unstable when the underlying data can mutate. When a UI component refreshes its data (new rows inserted, existing rows removed, or reordering), tracking selection by position causes the cursor to jump to a different item or reset unexpectedly. The user loses their place.

This isn't a bug in any particular framework — it's a category error. Position is the wrong identity for items that can move.

## The Cross-Cutting Pattern

**Track selection by stable identifier, not array position.** After refreshing data:

1. Save the unique ID of the currently selected item (before refresh)
2. Repopulate the data structure
3. Search for the saved ID in the new data
4. Move cursor to its new position (or apply fallback if not found)

This pattern applies across UI frameworks (React, Textual, etc.) and data structures (arrays, DataTables, lists). The implementation details vary, but the underlying insight is universal.

## Why This Works

Stable identifiers survive mutations:

- **Insertion** — Item moves to different index, ID unchanged
- **Removal** — ID disappears from dataset (handled by fallback)
- **Reordering** — Item moves to different index, ID unchanged

Position-based tracking fails in all three cases. Value-based tracking only fails when the item is removed, which is the one case where "lose your place" is semantically correct.

## Implementation: React

<!-- Source: erkdesk/src/renderer/App.tsx, selection preservation in refresh interval -->

See the `setSelectedIndex` callback in `erkdesk/src/renderer/App.tsx` (lines 48-55). The pattern:

- Save `issue_number` from `prevPlans[prevIndex]`
- Use `findIndex()` to locate it in `newPlans`
- Fall back to 0 if not found

**Why `findIndex()` instead of manual loop**: It handles the search and signals "not found" with `-1` in a single operation. The ternary `newIndex >= 0 ? newIndex : 0` becomes the complete fallback strategy.

## Implementation: Python/Textual

<!-- Source: src/erk/tui/widgets/plan_table.py, PlanDataTable.populate -->

See `PlanDataTable.populate()` in `src/erk/tui/widgets/plan_table.py` (lines 149-185). The pattern:

- Save `selected_key` (stringified `issue_number`) before `clear()`
- Also save `saved_cursor_row` as secondary fallback
- Loop through new rows to find matching `issue_number`
- If found, move cursor to that row
- If not found, clamp saved index to valid range

**Two-tier fallback**: This implementation prefers value-based restoration but accepts position-based as a fallback. The LBYL bounds check prevents invalid cursor positions when the list shrinks.

**Why both fallbacks**: The Textual implementation prioritizes "stay near where you were" over "reset to top". Different UX goal than React version.

## Fallback Strategy Decision Table

When the selected item disappears from the refreshed data, you must choose a fallback behavior:

| Strategy        | UX Intent                                 | When to Use                           |
| --------------- | ----------------------------------------- | ------------------------------------- |
| Reset to 0      | User should see latest/most important     | Priority-sorted lists (newest first)  |
| Preserve index  | User should see nearby context            | Navigable lists where position matters|
| Clear selection | Selection is meaningless without the item | Optional selection states             |

**Erk's choices:**

- **erkdesk (Electron)**: Reset to 0 — plans list is sorted newest-first, user expects to see latest plans
- **erk TUI**: Preserve index, clamped — user is navigating a stable list, context matters

Neither is "correct". The right choice depends on what the user is trying to accomplish.

## Historical Context

This pattern emerged from debugging cursor position resets in erkdesk. Initial implementation used array index, causing the cursor to jump when plans refreshed. The fix wasn't Electron-specific — it applied identically to the Textual-based TUI.

The generalized insight: **Mutable data structures need stable identity, not positional identity.** This applies beyond UI — any time you're tracking "which one" in a collection that can change.

## Related Topics

- [Textual Quirks](../textual/quirks.md) — `DataTable.clear()` behavior and cursor restoration
- [Erkdesk Auto-Refresh Patterns](../desktop-dash/erkdesk-auto-refresh-patterns.md) — Full refresh cycle including this pattern

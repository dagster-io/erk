---
title: TUI Filter Toggle Pattern
read_when:
  - "adding a filter toggle to the TUI dashboard"
  - "implementing server-side filtering in the TUI"
  - "adding keybindings that toggle dashboard state"
tripwires:
  - action: "adding a filter toggle to the TUI dashboard"
    warning: "Server-side filters (like author) must clear _data_cache on toggle. Client-side filters (like stack, objective) only re-filter cached rows. Follow the 6-component pattern in filter-toggle-pattern.md."
curated_in: erk-tui
---

# TUI Filter Toggle Pattern

Pattern for adding a filter toggle to the erk TUI dashboard. The author filter is the reference implementation.

## 6 Required Components

Each component below is demonstrated by the author filter toggle. The reference files are listed in the "Reference Implementation" section at the bottom.

<!-- Source: src/erk/tui/app.py, _show_all_users -->
<!-- Source: src/erk/tui/actions/filter_actions.py, action_toggle_all_users -->
<!-- Source: src/erk/tui/widgets/status_bar.py, set_author_filter -->
<!-- Source: src/erk/tui/screens/help_screen.py, help binding labels -->

### 1. Field Initialization (app.py)

Add a boolean field (e.g., `_show_all_users = False`) in the app's `__init__`. See `ErkDashApp` in `src/erk/tui/app.py`.

### 2. Action Handler (filter_actions.py)

Create a toggle action that flips the boolean, clears `_data_cache` (for server-side filters), updates the status bar, and calls `action_refresh()`. See `action_toggle_all_users()` in `src/erk/tui/actions/filter_actions.py`.

### 3. Status Bar Display (status_bar.py)

Add a setter method on StatusBar to display the filter state and trigger re-render. See `set_author_filter()` in `src/erk/tui/widgets/status_bar.py`.

### 4. Keybinding (app.py)

Add a `Binding` entry mapping a key to the toggle action. See the `BINDINGS` list in `src/erk/tui/app.py`.

### 5. Help Entry (help_screen.py)

Add a `Label` describing the keybinding in the help screen. See `src/erk/tui/screens/help_screen.py`.

### 6. Data Provider Integration

Pass the filter state to the data provider when fetching. For server-side filters, the toggle value determines the API query parameter (e.g., `active_creator = None if self._show_all_users else self._original_creator`). See the data loading logic in `src/erk/tui/app.py`.

## Server-Side vs Client-Side Filters

- **Server-side** (author): Clears `_data_cache` and calls `action_refresh()` to re-fetch from GitHub API
- **Client-side** (text, stack, objective): Re-filters cached `_all_rows` without re-fetching

The author filter is server-side because GitHub's API supports creator filtering — filtering locally would require fetching all plans first.

## Composing Filters

All filters coexist: text filter, stack filter, objective filter, and author filter. Client-side filters apply via `_apply_filter_and_sort()`. Server-side filters affect the fetch parameters.

## Reference Implementation

- **Action handler:** `src/erk/tui/actions/filter_actions.py` — `action_toggle_all_users()`
- **App state:** `src/erk/tui/app.py` — `_show_all_users` field and binding
- **Status bar:** `src/erk/tui/widgets/status_bar.py` — `set_author_filter()`
- **Help screen:** `src/erk/tui/screens/help_screen.py` — line 90

## Related Topics

- [TUI Streaming Output Patterns](streaming-output.md) — status bar update patterns

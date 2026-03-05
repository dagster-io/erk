# Toggle Author Filter in erk TUI

## Context

Currently, the erk TUI (`erk dash`) filters plans/objectives to the authenticated user by default (via `--creator` at startup). The only way to see all users' data is to restart with `--all-users` / `-A`. The user wants to toggle the author filter on/off interactively within the TUI, similar to how `o` toggles objective filter and `t` toggles stack filter.

The key difference from objective/stack filters (which are client-side) is that the creator filter is applied **server-side** via the GitHub API. Toggling it requires re-fetching data.

## Approach

Use the `a` keybinding to toggle between "my plans" and "all users" mode. When toggled, clear the data cache and re-fetch.

## Files to Modify

### 1. `src/erk/tui/app.py` - Add state and modify data loading

- Add `_show_all_users: bool = False` field in `__init__`
- Store the original creator: `_original_creator: str | None = filters.creator`
- In `_load_data()` (line ~209): use `creator=None` when `_show_all_users` is True, otherwise use `self._original_creator`
- In `BINDINGS`: add `Binding("a", "toggle_all_users", "All Users", show=False)`

### 2. `src/erk/tui/actions/filter_actions.py` - Add toggle action

Add `action_toggle_all_users` method:
- Toggle `self._show_all_users`
- Clear `self._data_cache` (invalidate all cached views since they were fetched with the old creator)
- Trigger `self.action_refresh()` to re-fetch
- Show status message: "Showing all users" or "Showing my plans"

### 3. `src/erk/tui/widgets/status_bar.py` - Show author mode indicator

- Add `_author_filter: str | None = None` field and `set_author_filter(label: str | None)` method
- In `_update_display()`: include the author filter state in the parts list (e.g., "author: all" or "author: schrockn")
- Update key hints to include `a:users`

### 4. `src/erk/tui/screens/help_screen.py` - Add help entry

- Add `"a       Toggle all users / my plans"` in the "Filter & Sort" section

## Verification

1. Run `erk dash` (defaults to my plans only)
2. Press `a` - should re-fetch and show all users' plans, status bar shows "all users"
3. Press `a` again - should re-fetch and show only my plans, status bar shows username
4. Switch views (1/2/3) while in "all users" mode - should maintain the all-users setting
5. Run existing TUI tests to ensure no regressions

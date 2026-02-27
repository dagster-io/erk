# Make ViewBar tabs clickable in erk dash

## Context

The erk dash TUI has a view bar at the top showing `1:Planned PRs  2:Learn  3:Objectives`. Currently tabs can only be switched via keyboard shortcuts (1, 2, 3) or arrow keys. The user wants to also click on tab labels to switch views.

## Approach

Follow the existing click-handling pattern used by `PlanDataTable` (Message class + `@on` handler in app).

### 1. Update `ViewBar` widget (`src/erk/tui/widgets/view_bar.py`)

- Add a `ViewTabClicked(Message)` inner class with a `view_mode: ViewMode` field
- During `_refresh_display()`, compute and store tab regions as a list of `(start_x, end_x, ViewMode)` tuples based on label lengths
- Add `on_click(self, event: Click)` handler that:
  - Computes content-relative x by subtracting left padding (1 char from `padding: 0 1`)
  - Finds which tab region contains the click x coordinate
  - Posts `ViewTabClicked(view_mode)` if a tab was hit

### 2. Handle message in app (`src/erk/tui/app.py`)

- Add `@on(ViewBar.ViewTabClicked)` handler that calls `self._switch_view(event.view_mode)`

### 3. Add test (`tests/tui/test_view_bar.py`)

- Test that `_tab_regions` are computed correctly after refresh
- Test that click at various x positions maps to the right tab

## Files to modify

- `src/erk/tui/widgets/view_bar.py` — add Message, regions tracking, click handler
- `src/erk/tui/app.py` — add `@on(ViewBar.ViewTabClicked)` handler
- `tests/tui/test_view_bar.py` — add region/click tests

## Verification

- Run `uv run pytest tests/tui/test_view_bar.py` for unit tests
- Run `erk dash -i` and click each tab label to verify navigation works

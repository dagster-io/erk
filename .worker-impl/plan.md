# Add Left/Right Arrow View Cycling to erk dash

## Context

The erk dash TUI main screen supports switching between three views (Plans, Learn, Objectives) via `1`, `2`, `3` hotkeys. The user wants left/right arrow keys to cycle through these views as well, for more natural navigation.

## Changes

### `src/erk/tui/views/types.py`

Add a helper function to get the next/previous `ViewMode` by cycling through `VIEW_CONFIGS`:

```python
def get_next_view_mode(current: ViewMode) -> ViewMode:
    modes = [c.mode for c in VIEW_CONFIGS]
    idx = modes.index(current)
    return modes[(idx + 1) % len(modes)]

def get_previous_view_mode(current: ViewMode) -> ViewMode:
    modes = [c.mode for c in VIEW_CONFIGS]
    idx = modes.index(current)
    return modes[(idx - 1) % len(modes)]
```

### `src/erk/tui/app.py`

1. Add two bindings to `BINDINGS` (line ~79):
   ```python
   Binding("right", "next_view", "Next View", show=False),
   Binding("left", "previous_view", "Previous View", show=False),
   ```

2. Add two action methods:
   ```python
   def action_next_view(self) -> None:
       self._switch_view(get_next_view_mode(self._view_mode))

   def action_previous_view(self) -> None:
       self._switch_view(get_previous_view_mode(self._view_mode))
   ```

## Files Modified

- `src/erk/tui/views/types.py` — add `get_next_view_mode()` and `get_previous_view_mode()`
- `src/erk/tui/app.py` — add bindings and action methods

## Verification

- Run existing TUI tests: `pytest tests/tui/`
- Manual: `erk dash -i`, press left/right to cycle Plans → Learn → Objectives → Plans (wrapping)
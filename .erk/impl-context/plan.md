# Fix: Modal keystrokes leaking to underlying view

## Context

When a modal screen is open in `erk dash -i`, keystrokes that aren't handled by the modal leak through to the app-level bindings and mutate the underlying view. For example, pressing "l" then "s" to dispatch a job also triggers `action_toggle_sort()` on the main screen. The user expects:

1. No keystroke should affect the view while a modal is open
2. Any unmapped keystroke should dismiss the modal

This affects **all three modal screens** — not just LaunchScreen.

## Root Cause

`LaunchScreen.on_key()` only calls `event.prevent_default()` when the key matches a mapped command. Unmapped keys pass through to the app. `HelpScreen` and `PlanBodyScreen` don't have `on_key()` at all — they rely solely on BINDINGS, so any key not in BINDINGS leaks to the parent.

## Plan

### 1. Fix `LaunchScreen.on_key()` — consume all keys, dismiss on unmapped

**File:** `src/erk/tui/screens/launch_screen.py` (lines 122-127)

Change `on_key` to prevent all key events from propagating. Unmapped keys dismiss the modal (same as pressing Escape):

```python
def on_key(self, event: Key) -> None:
    """Handle key press—dispatch to command if mapped, dismiss otherwise."""
    event.prevent_default()
    event.stop()
    command_id = self._key_to_command_id.get(event.key)
    if command_id is not None:
        self.dismiss(command_id)
    elif event.key not in ("escape", "q"):
        self.dismiss(None)
```

The `escape`/`q` guard avoids double-dismiss since those are already in BINDINGS.

### 2. Add `on_key()` to `HelpScreen` — dismiss on any key

**File:** `src/erk/tui/screens/help_screen.py`

The footer already says "Press any key to close" but doesn't implement it. Add:

```python
def on_key(self, event: Key) -> None:
    """Dismiss on any key press."""
    event.prevent_default()
    event.stop()
    if event.key not in ("escape", "q", "question_mark"):
        self.dismiss()
```

### 3. Add `on_key()` to `PlanBodyScreen` — dismiss on any unmapped key

**File:** `src/erk/tui/screens/plan_body_screen.py`

```python
def on_key(self, event: Key) -> None:
    """Consume all keys while modal is open; dismiss on unmapped keys."""
    event.prevent_default()
    event.stop()
    if event.key not in ("escape", "q", "space"):
        self.dismiss()
```

## Files to Modify

- `src/erk/tui/screens/launch_screen.py`
- `src/erk/tui/screens/help_screen.py`
- `src/erk/tui/screens/plan_body_screen.py`

## Verification

- Run existing TUI tests: `pytest tests/tui/`
- Manual: `erk dash -i` → press "?" for help → press "s" → help closes, view is NOT sorted
- Manual: press "l" for launch → press unmapped key → modal closes, view unchanged
- Manual: press "l" then "s" on a dispatchable plan → dispatches, view NOT sorted

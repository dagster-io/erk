# Add arrow key navigation to ObjectiveNodesScreen

## Context

The ObjectiveNodesScreen (`src/erk/tui/screens/objective_nodes_screen.py`) only binds `j`/`k` for cursor movement. Arrow keys should also work. The screen has custom `action_cursor_down`/`action_cursor_up` methods that skip phase separator rows — arrow keys must route through these same actions.

## Problem

`j`/`k` work because DataTable doesn't handle them natively, so they bubble up to the screen's BINDINGS. Arrow keys (`down`/`up`) ARE handled by DataTable natively, so they get consumed before reaching the screen — bypassing the separator-skipping logic.

## Change

**File:** `src/erk/tui/screens/objective_nodes_screen.py` (lines 148-149)

Add two bindings with `priority=True` so they intercept before DataTable's native handling:

```python
BINDINGS = [
    Binding("escape", "dismiss", "Close"),
    Binding("q", "dismiss", "Close"),
    Binding("space", "dismiss", "Close"),
    Binding("j", "cursor_down", "Down", show=False),
    Binding("k", "cursor_up", "Up", show=False),
    Binding("down", "cursor_down", "Down", show=False, priority=True),
    Binding("up", "cursor_up", "Up", show=False, priority=True),
    Binding("p", "open_pr", "Open PR", show=False),
    Binding("o", "open_objective", "Objective", show=False),
    Binding("enter", "open_detail", "Detail", show=False),
    Binding("ctrl+p", "command_palette", "Commands", show=False),
]
```

`priority=True` is required because Textual's binding resolution order is: focused widget → containers → screen → app. Without priority, the DataTable widget would handle `down`/`up` directly (moving the cursor without separator-skipping).

## Verification

1. Run `erk dash -i`, navigate to an objective, press Enter to open ObjectiveNodesScreen
2. Verify up/down arrow keys navigate rows and skip phase separator rows
3. Verify j/k still work identically

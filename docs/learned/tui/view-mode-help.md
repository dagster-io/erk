---
title: View-Mode-Aware Help Screen
read_when:
  - "modifying the TUI help screen"
  - "adding view-specific actions to the TUI"
  - "understanding ViewMode-conditional rendering"
curated_in: erk-tui
---

# View-Mode-Aware Help Screen

The TUI `HelpScreen` accepts a `view_mode: ViewMode` parameter and conditionally renders help content based on the active view (plans vs objectives).

## Implementation Pattern

<!-- Source: src/erk/tui/screens/help_screen.py -->

The `HelpScreen.__init__()` stores `view_mode` as an instance variable. A helper method `_is_objectives_view()` wraps the check. The `compose()` method uses this to branch rendering:

```python
def compose(self) -> ComposeResult:
    is_objectives = self._is_objectives_view()
    # ... shared sections ...
    if is_objectives:
        yield Label("Enter   View objective details", ...)
    else:
        yield Label("Enter   View plan details", ...)
```

## Conditional Sections

### Actions Section

- **Objectives view**: Shows objective-specific actions (view details, check objective)
- **Plans view**: Shows plan-specific actions (view details, implement, dispatch)

### Filter & Sort Section

Hides filters not applicable to the current view. For example, stack filter is only relevant in plans view.

## Documented Bindings

The help screen includes bindings that may not be obvious from the shortcut inventory:

- `n` — Open CI run in browser
- `left/right` — Switch between views

## Related Documentation

- [Keyboard Shortcuts Inventory](keyboard-shortcuts.md) — Full binding list
- [TUI Architecture](architecture.md) — Overall TUI design

---
name: erk-tui-textual-quirks
description: Textual framework gotchas for DataTable, CSS, Rich markup, and testing
---

# Textual Framework Quirks

**Read this when**: Hitting Textual framework issues, working with DataTable, CSS styling, Rich markup, or writing TUI tests.

## DataTable Gotchas

### Cursor Type Initialization

Set `cursor_type` via `__init__()`, not as a class attribute:

```python
# CORRECT
class MyTable(DataTable):
    def __init__(self) -> None:
        super().__init__(cursor_type="row")

# WRONG — may not take effect
class MyTable(DataTable):
    cursor_type = "row"
```

### Clear + Restore Pattern

`DataTable.clear()` resets the cursor position. To preserve selection:

1. Save current cursor key/position
2. Call `clear()`
3. Re-add all rows
4. Restore cursor by key first, then fall back to index

### Attribute Name Conflicts

Avoid `_filters` as an attribute name — conflicts with Textual internals. Use a more specific name.

### Column Keys

Column key is a data binding contract — must match data field name. Silent failure when mismatched.

## Rich Markup Escaping

### Text() Wrapping in DataTable

**Critical**: Always wrap user data in `Text(value)` when adding cell values:

```python
from rich.text import Text

# WRONG — "[critical] error" becomes Rich styled tag
table.add_row("[critical] error", ...)

# CORRECT — renders literal text
table.add_row(Text("[critical] error"), ...)
```

This is different from Rich CLI output (which uses `escape_markup()`). DataTable specifically needs `Text()` wrapping.

Apply to: user titles, plan prefixes, file paths, technical content — anything with potential `[brackets]`.

### Status Bar / Static with Subprocess Output

Use `markup=False` parameter to prevent bracket parsing in plain text displays.

### URL Markup

Always quote URLs in link tags and escape display text:

```python
f'[link="{url}"]{escaped_text}[/link]'
```

## CSS Patterns

### ModalScreen Overlay

`ModalScreen` requires explicit CSS for the overlay. Without it, clicking outside the modal does nothing.

### DOM ID Reuse

Don't reuse the same DOM element ID across loading/empty/content states. `query_one()` returns the wrong element silently when IDs are reused across lifecycle phases. Use unique IDs per phase.

## Event Handling

### Click Handlers

Need BOTH `prevent_default()` AND `stop()` to prevent base DataTable handling:

```python
def on_click(self, event: Click) -> None:
    event.prevent_default()
    event.stop()
    # ... custom handling
```

### get_system_commands() Location

Must be overridden on the **App class**, not Screen class:

```python
# WRONG — Textual never calls this on screens
class MyScreen(ModalScreen):
    def get_system_commands(self, screen): ...

# CORRECT
class MyApp(App):
    def get_system_commands(self, screen): ...
```

### \_render() Name Conflict

Textual's LSP reserves `_render()`. Use `_refresh_display()` for widget refresh methods.

## Background Workers

- Use `run_worker(exclusive=True)` to cancel running workers before starting new ones
- `call_from_thread()` is the only safe way to update widgets from worker context
- Match base class signature for async overrides

## Testing Patterns

### App Configuration

Always set `refresh_interval=0` in test apps to disable auto-refresh (prevents timing-dependent test failures).

### Screen Transitions

Use multiple `await pilot.pause()` calls — screen transitions need 2+ pauses to complete.

### Async Action Completion

After key presses or actions that trigger async work:

```python
await pilot.press("enter")
await pilot.pause()  # Wait for async completion
```

### ModalScreen Callbacks

`ModalScreen` callback receives `T | None`, not just `T`. Always handle the None case.

## Widget Development Reference

**Reference implementations** for common patterns:

- `HelpScreen` — view-mode-aware content rendering
- `PlanDetailScreen` — data fetching modal with error handling
- `CommandOutputPanel` — streaming subprocess output display
- `clickable_link` — Rich markup URL generation

CSS and widgets live in:

- `src/erk/tui/styles/` — CSS files
- `src/erk/tui/widgets/` — Widget implementations

## Source Documents

Distilled from: `textual/quirks`, `textual/background-workers`, `textual/testing`, `textual/datatable-markup-escaping`, `textual/widget-development`

---
title: Textual API Quirks and Workarounds
read_when:
  - "working with Textual TUI framework"
  - "debugging DataTable, App, or CSS issues in Textual"
  - "writing tests for Textual applications"
---

# Textual API Quirks and Workarounds

This document captures API quirks discovered while building the erk dash TUI with Textual.

## DataTable Quirks

### cursor_type Must Be Set via `__init__`

**Problem**: `cursor_type` is a `Reactive[CursorType]`, not a plain attribute. Setting it as a class attribute causes pyright errors:

```python
# WRONG - causes type error
class MyTable(DataTable):
    cursor_type = "row"  # Type error: Literal['row'] not assignable to Reactive[CursorType]
```

**Solution**: Pass to `super().__init__()`:

```python
# CORRECT
class MyTable(DataTable):
    def __init__(self) -> None:
        super().__init__(cursor_type="row")
```

### Avoid `_filters` Attribute Name

**Problem**: DataTable has an internal `_filters` attribute of type `list[LineFilter]`. Naming your own attribute `_filters` causes type conflicts when pyright analyzes the code.

**Solution**: Use a different name like `_plan_filters` or `_my_filters`.

### clear() Resets Cursor Position

**Problem**: Calling `DataTable.clear()` resets the cursor to row 0. If you're refreshing data, the user loses their place.

**Solution**: Save cursor position before clear, restore after repopulating:

```python
def populate(self, rows: list[RowData]) -> None:
    # Save current selection by row key
    selected_key = None
    if self._rows and self.cursor_row is not None:
        selected_key = str(self._rows[self.cursor_row].id)

    saved_cursor_row = self.cursor_row

    self.clear()
    for row in rows:
        self.add_row(*values, key=str(row.id))

    # Restore by key first, fall back to row index
    if rows and selected_key:
        for idx, row in enumerate(rows):
            if str(row.id) == selected_key:
                self.move_cursor(row=idx)
                return

    # Fall back to saved index (clamped)
    if saved_cursor_row is not None and saved_cursor_row >= 0:
        self.move_cursor(row=min(saved_cursor_row, len(rows) - 1))
```

### Enter Key May Be Captured

**Problem**: DataTable may capture the Enter key for its own row selection behavior, preventing app-level Enter bindings from firing.

**Solution**: Handle the `RowSelected` event instead of (or in addition to) binding Enter:

```python
@on(DataTable.RowSelected)
def on_row_selected(self, event: DataTable.RowSelected) -> None:
    # Handle Enter/double-click on row
    self.action_open_issue()
```

### Click Handlers Need Both `prevent_default()` and `stop()`

**Problem**: When overriding `on_click` in a DataTable subclass to handle clicks on specific columns (e.g., copying text to clipboard), using only `event.stop()` doesn't prevent the base DataTable from handling the click. The click still triggers row selection and emits `RowSelected`, which may open a modal or trigger other unwanted behavior.

**Why this happens**: `event.stop()` only prevents the event from bubbling up to parent widgets. Textual still calls handlers on base classes unless you use `prevent_default()`.

**Solution**: Use both `event.prevent_default()` and `event.stop()`:

```python
def on_click(self, event: Click) -> None:
    coord = self.hover_coordinate
    if coord is None:
        return

    row_index = coord.row
    col_index = coord.column

    # Handle click on specific column
    if col_index == self._my_column_index:
        if row_index < len(self._rows):
            self.post_message(self.MyColumnClicked(row_index))
            event.prevent_default()  # Stop base class from handling
            event.stop()  # Stop bubbling to parent widgets
            return
```

**Key insight**:

- `event.stop()` → prevents bubbling to parent widgets in the DOM
- `event.prevent_default()` → prevents Textual from calling base class handlers

Without `prevent_default()`, DataTable's internal click handling still fires, moving the cursor and potentially triggering `RowSelected`.

## App Quirks

### Don't Override `action_quit` Synchronously

**Problem**: The base `App.action_quit` is an async method. Overriding it with a sync method causes pyright errors about incompatible return types.

**Solution**: Use a different action name:

```python
# WRONG
def action_quit(self) -> None:  # Type error: incompatible override
    self.exit()

# CORRECT
BINDINGS = [Binding("q", "exit_app", "Quit")]

def action_exit_app(self) -> None:
    self.exit()
```

### Footer Widget Hides Custom Status Bars

**Problem**: Textual's built-in `Footer` widget docks at the bottom and will visually override any custom status bar you create, even if your status bar also docks at bottom.

**Solution**: If you want a custom status bar with specific content (countdown timers, custom messages), don't use `Footer`. Create your own `Static` widget with `dock: bottom`.

### Async Data Loading Pattern

**Problem**: When loading data in a background thread with `run_in_executor`, you might try to use `call_from_thread` to update the UI. This fails in test context with "must run in different thread" error.

**Solution**: Since `_load_data` is already async and we `await` the executor result, we're back on the main thread. Just call the update method directly:

```python
async def _load_data(self) -> None:
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, self._provider.fetch_plans, self._filters)

    # WRONG - fails in tests
    # self.call_from_thread(self._update_table, rows)

    # CORRECT - we're already on main thread after await
    self._update_table(rows)
```

## Testing Quirks

### pytest-asyncio Required

**Problem**: Textual's `app.run_test()` is async. Without pytest-asyncio, tests fail with "async def functions are not natively supported".

**Solution**: Add pytest-asyncio to dev dependencies and configure in pyproject.toml:

```toml
[dependency-groups]
dev = [
    "pytest-asyncio>=0.23.0",
    # ...
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Use `pilot.pause()` for Async Operations

**Problem**: After pressing keys or triggering actions, the UI might not have updated yet.

**Solution**: Use `await pilot.pause()` to let async operations complete:

```python
async def test_help_screen(self) -> None:
    async with app.run_test() as pilot:
        await pilot.press("?")
        await pilot.pause()  # Wait for screen push
        await pilot.pause()  # Extra pause for transitions

        assert isinstance(app.screen_stack[-1], HelpScreen)
```

## CSS/Styling Quirks

### Widget Visibility with `display`

**Problem**: Setting `widget.display = False` hides the widget but it still takes up space in some layouts.

**Solution**: For loading states, use a container and toggle visibility of children, or use `widget.styles.display = "none"` for complete removal from layout.

## Rich Markup Quirks

### URLs Must Be Quoted in Link Tags

**Problem**: Rich markup's `[link=...]` syntax fails silently during widget creation but crashes at render time if the URL is unquoted:

```python
# WRONG - causes MarkupError at render time
f"[link={url}]{text}[/link]"
```

**Error signature:**

```
MarkupError: Expected markup value (found '://github.com/...')
```

The `https` prefix appears to be consumed by the parser as a markup modifier.

**Solution**: Always quote URLs in link tags and escape display text:

```python
from rich.markup import escape as escape_markup

# CORRECT - escape display text, quote URL, handle special chars in URL
def make_link(url: str, text: str) -> str:
    escaped_text = escape_markup(text)
    safe_url = url.replace('"', "%22")  # Escape quotes in URL
    return f'[link="{safe_url}"]{escaped_text}[/link]'

# Use markup=False for Labels with user-provided content that doesn't need links
yield Label(user_title, classes="row", markup=False)
```

This applies to any `Label(..., markup=True)` or other widget accepting Rich markup strings.

**Key patterns:**

1. Use `escape_markup()` on display text to prevent `[brackets]` from being parsed
2. Quote URLs and escape any `"` characters that might appear in them
3. Set `markup=False` on Labels that show user content without links

## General Recommendations

1. **Use type annotations** - Textual uses Reactives heavily; proper types catch issues early
2. **Test with pilot** - Real TUI behavior differs from unit tests; use `run_test()` context
3. **Check Textual version** - API changes between versions; pin to `>=3.0.0` for stability
4. **Avoid name collisions** - Textual widgets have many internal attributes; use prefixes

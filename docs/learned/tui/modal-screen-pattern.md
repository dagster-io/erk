---
title: TUI Modal Screen Pattern
read_when:
  - "adding a new modal screen to the TUI"
  - "implementing a ModalScreen subclass"
  - "displaying detail views or confirmation dialogs"
tripwires:
  - action: "creating a ModalScreen without CSS for dismiss behavior"
    warning: "ModalScreen requires explicit CSS for the overlay. Without it, clicking outside the modal does nothing."
  - action: "calling widget methods from @work(thread=True) without call_from_thread()"
    warning: "Background thread widget mutations cause silent UI corruption. Use self.app.call_from_thread(callback, ...)."
  - action: "using inverted key check in on_key() modal dismiss logic"
    warning: "if event.key not in (...) is WRONG for dismiss logic — it swallows dismiss keys. Use if event.key in (...) to check for positive dismiss. Regression caused by stacked PR merge order."
    score: 7
---

# TUI Modal Screen Pattern

Checklist for implementing a new modal screen in the erk TUI.

## 7-Element Checklist

### 1. ModalScreen Subclass

Extend `ModalScreen` (not `Screen`) to get overlay dismiss behavior:

```python
from textual.screen import ModalScreen

class MyDetailScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]
```

### 2. CSS for Layout

Define CSS either inline (via `DEFAULT_CSS`) or in a `.tcss` file in `src/erk/tui/styles/`. The modal needs explicit sizing since it doesn't fill the screen:

```css
MyDetailScreen {
  align: center middle;
}

MyDetailScreen > #content {
  width: 80%;
  height: 80%;
  background: $surface;
  border: thick $accent;
  padding: 1 2;
}
```

### 3. BINDINGS for Navigation

At minimum, bind `escape` to dismiss. Add key bindings for any actions the modal supports.

### 4. @work(thread=True) for Data Fetching

Fetch data in a background worker to keep the UI responsive:

```python
@work(thread=True)
def _fetch_data(self) -> None:
    try:
        result = self._provider.fetch_something(self._id)
        self.app.call_from_thread(self._on_data_loaded, result)
    except Exception as e:
        self.app.call_from_thread(self._on_error, str(e))
```

### 5. call_from_thread() Bridge

All widget mutations from background threads must go through `call_from_thread()`:

```python
def _on_data_loaded(self, data: MyData) -> None:
    self.query_one("#content", Static).update(data.formatted)
    self.query_one("#loading", LoadingIndicator).display = False
```

### 6. Error Boundary

Wrap the entire worker body in try/except. This is an approved EAFP exception for UI error boundaries — it prevents silent worker failures.

### 7. Loading Placeholder

Show a loading indicator while data is being fetched. Use unique DOM element IDs per lifecycle phase (loading vs content) to avoid `query_one()` returning the wrong element.

### 8. When to Override on_key()

For modals that need to consume all keypresses (preventing the parent app from handling them), override `on_key()` with `event.prevent_default()` + `event.stop()`:

```python
def on_key(self, event: Key) -> None:
    """Consume all keys; dismiss on specific keys."""
    event.prevent_default()
    event.stop()
    if event.key in ("escape", "q", "space"):
        self.dismiss()
```

**Pattern:** Call `event.prevent_default()` and `event.stop()` first (unconditionally), then check which key was pressed.

**Inverted logic tripwire:** Using `if event.key not in (...)` to dismiss causes silent bugs — keys that should dismiss the modal get swallowed instead. Always use `if event.key in (...)` for the positive dismiss check.

**Screens using this pattern:**

| Screen           | Dismiss Keys     | Notes                                       |
| ---------------- | ---------------- | ------------------------------------------- |
| `HelpScreen`     | escape, q, ?     | Closes help overlay                         |
| `PlanBodyScreen` | escape, q, space | Closes plan body view                       |
| `LaunchScreen`   | Any unmapped key | Dispatches mapped keys, dismisses on others |

`LaunchScreen` uses a dynamic key map (`self._key_to_command_id`) and dismisses with `None` for unmapped keys, making it a command dispatch pattern rather than a simple dismiss.

## Reference Implementations

- `UnresolvedCommentsScreen` — fetches and displays PR review comments
- `PlanBodyScreen` — fetches and displays plan body content
- `PlanDetailScreen` — displays plan details with markdown rendering
- `ObjectiveNodesScreen` — displays objective nodes with async data loading, phase separators, PR data enrichment, and next-node highlighting

## Related Documentation

- [TUI Architecture](architecture.md) — Overall TUI design and data layer
- [Textual Async Best Practices](textual-async.md) — Error boundary pattern details

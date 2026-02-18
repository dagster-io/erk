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

## Reference Implementations

- `UnresolvedCommentsScreen` — fetches and displays PR review comments
- `IssueBodyScreen` — fetches and displays GitHub issue body content
- `PlanDetailScreen` — displays plan details with markdown rendering

## Related Documentation

- [TUI Architecture](architecture.md) — Overall TUI design and data layer
- [Textual Async Best Practices](textual-async.md) — Error boundary pattern details

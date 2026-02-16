---
title: TUI Streaming Output Patterns
read_when:
  - "displaying streaming command output in TUI"
  - "executing long-running commands with progress"
  - "cross-thread UI updates in Textual"
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
---

# TUI Streaming Output Patterns

Patterns for displaying streaming command output in the Erk TUI without blocking the UI thread.

For subprocess execution strategies (streaming vs executor, `stdin=subprocess.DEVNULL` requirement), see [Command Execution Strategies](command-execution.md).

## Architecture Components

1. **Background Thread** - Reads subprocess output via `subprocess.PIPE`
2. **Output Widget** - `CommandOutputPanel` (`src/erk/tui/widgets/command_output.py`) displays streaming content
3. **Cross-Thread Bridge** - `app.call_from_thread()` safely updates UI from background thread

## Critical: Threading Safety with `call_from_thread`

`call_from_thread` is a Textual `App`-level method, NOT available on `Widget`. This is a common mistake:

**WRONG:**

```python
class MyWidget(Widget):
    def update_from_thread(self):
        # BAD: self.call_from_thread is not available on Widget
        self.call_from_thread(self._update_ui)
```

**CORRECT:**

```python
class MyWidget(Widget):
    def __init__(self, app: App):
        super().__init__()
        self._app = app

    def update_from_thread(self):
        # GOOD: Use app.call_from_thread
        self._app.call_from_thread(self._update_ui)

    def _update_ui(self):
        # This runs in the main thread, safe to update widgets
        self.update("New content")
```

Production usage: see `src/erk/tui/screens/plan_detail_screen.py` and `src/erk/tui/app.py`.

## Widget Selection for Streaming Output

| Widget    | Use When                   | Max Lines          | Auto-Scroll |
| --------- | -------------------------- | ------------------ | ----------- |
| `Log`     | Simple line-by-line output | Yes (configurable) | Yes         |
| `RichLog` | Rich text with markup      | Yes (configurable) | Yes         |
| `Static`  | Small, static content      | No limit           | No          |

**For streaming command output, use `RichLog`** — the production `CommandOutputPanel` uses `RichLog` with `highlight=True` and `markup=True`.

## Related Documentation

- [Textual Async Best Practices](textual-async.md)
- [Command Execution Strategies](command-execution.md)

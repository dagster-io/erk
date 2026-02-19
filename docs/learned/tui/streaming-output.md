---
title: TUI Streaming Output Patterns
read_when:
  - "displaying streaming command output in TUI"
  - "executing long-running commands with progress"
  - "cross-thread UI updates in Textual"
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
tripwires:
  - action: "accessing _status_bar without null guard"
    warning: "Guard _status_bar access with `if self._status_bar is not None:` — timing issue during widget lifecycle can cause AttributeError."
  - action: "using subprocess.Popen without bufsize=1 for streaming"
    warning: "Use bufsize=1 with text=True for line-buffered streaming Popen output. Without it, output may be block-buffered."
  - action: "displaying subprocess output in plain text widgets without stripping ANSI"
    warning: "Use click.unstyle() before displaying subprocess output in plain text widgets. Raw ANSI codes render as garbage."
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

## Pattern 3: Status Bar Streaming

For lightweight progress display (not full command output), use `subprocess.Popen` with status bar updates via `call_from_thread()`. This pattern is used by `_land_pr_async()` in `src/erk/tui/app.py`.

### Key Components

1. **Line-buffered subprocess**: `subprocess.Popen` with `bufsize=1`, `text=True` for real-time line output
2. **Thread-safe status bar updates**: `call_from_thread()` to update the status bar from the background thread
3. **ANSI code stripping**: `click.unstyle()` removes ANSI escape codes before displaying in plain text widgets
4. **Output collection**: Lines stored in `output_lines` list for error context extraction on failure
5. **Diagnostic helper**: `_last_meaningful_line(lines)` returns the last non-empty line for error messages

### Pattern

```python
@work(thread=True)
def _run_async(self) -> None:
    output_lines: list[str] = []
    proc = subprocess.Popen(
        ["erk", "exec", "some-command"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        bufsize=1,
        text=True,
    )
    if proc.stdout is not None:
        for line in proc.stdout:
            clean = click.unstyle(line.rstrip())
            output_lines.append(clean)
            self.call_from_thread(self._set_status, clean)
    return_code = proc.wait()
    if return_code != 0:
        msg = _last_meaningful_line(output_lines) or "Unknown error"
        self.call_from_thread(self.notify, msg, severity="error")
```

### Production Usage

- `_push_streaming_detail()` in `src/erk/tui/app.py` — Pushes a streaming detail screen for long-running commands (land PR, submit to queue, etc.). Used with an `on_success` callback (e.g., `_on_land_success`) for post-completion actions like objective updates.

## Related Documentation

- [Textual Async Best Practices](textual-async.md)
- [Command Execution Strategies](command-execution.md)
- [TUI Subprocess Testing](../testing/tui-subprocess-testing.md) - Testing patterns for subprocess-based TUI features

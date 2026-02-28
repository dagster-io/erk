---
title: TUI Multi-Operation Tracking
read_when:
  - "adding a new background operation to the TUI"
  - "implementing status bar progress for a workflow command"
  - "debugging operation lifecycle or stuck operations"
tripwires:
  - action: "calling start_operation() without a matching finish_operation() in the error path"
    warning: "Always call finish_operation() in both success and error paths. Use try/finally or explicit error handling. Missing finish calls leave ghost operations in the status bar."
  - action: "constructing op IDs without the {action}-{resource}-{id} pattern"
    warning: "Op IDs must follow the convention: f'{action}-{resource_type}-{resource_id}' (e.g., 'land-pr-456', 'close-plan-123'). Non-unique IDs cause operations to overwrite each other."
  - action: "using subprocess.run() instead of _run_streaming_operation() for TUI commands"
    warning: "TUI background operations must use _run_streaming_operation() for live progress. subprocess.run() blocks without streaming and produces no status bar updates."
  - action: "calling self.notify() or self._finish_operation() directly from a background thread"
    warning: "Use self.call_from_thread() for all UI updates from @work(thread=True) methods. Direct calls cause thread-safety violations."
---

# TUI Multi-Operation Tracking

The TUI supports multiple concurrent background operations with live progress display in the status bar. Operations are tracked via a registry pattern with start/update/finish lifecycle methods.

## Architecture

### \_OperationState

Frozen dataclass in `src/erk/tui/widgets/status_bar.py`. Stores the current label and progress text for a single operation. See source file for implementation details.

### Operations Registry

`_operations: dict[str, _OperationState]` in `src/erk/tui/widgets/status_bar.py` maps op IDs to their current state. Supports multiple concurrent operations; the most recently updated one is displayed.

## Lifecycle Methods

All in `src/erk/tui/widgets/status_bar.py`:

| Method                              | Purpose                                           |
| ----------------------------------- | ------------------------------------------------- |
| `start_operation(op_id, label)`     | Register new operation, add "running" CSS class   |
| `update_operation(op_id, progress)` | Update progress text (no-op if op_id not found)   |
| `finish_operation(op_id)`           | Remove operation, remove "running" class if empty |

## Op ID Convention

Pattern: `f"{action}-{resource_type}-{resource_id}"`

Examples:

- `"close-plan-123"` — closing plan #123
- `"land-pr-456"` — landing PR #456
- `"dispatch-plan-123"` — dispatching plan #123
- `"fix-conflicts-pr-456"` — fixing conflicts for PR #456
- `"address-pr-456"` — addressing PR #456

The op ID uniquely identifies a concurrent operation. Multiple operations can run simultaneously; the status bar displays the most recently updated one.

## Streaming Subprocess Integration

`_run_streaming_operation()` in `src/erk/tui/app.py`:

1. Uses `subprocess.Popen` with `bufsize=1` and `text=True` for line-buffered output
2. Merges stdout and stderr (`stderr=subprocess.STDOUT`)
3. Strips ANSI escape codes with `click.unstyle()` before display
4. Streams each line to status bar via `self.call_from_thread()`
5. Returns `_OperationResult` with success status, output lines, and return code

## Toast + Status Bar Pattern

Status bar shows live progress during operations. On completion:

**Success path:** Finish the operation via `self.call_from_thread()`, display a success toast via `self.notify()` with `timeout=3`, and refresh the view.

**Error path:** Extract the last line of output, finish the operation, and display an error toast with `severity="error"` and `timeout=5` for longer visibility.

All UI updates from background operations must use `self.call_from_thread()` to maintain thread safety. See `src/erk/tui/app.py` for implementation details.

## Multi-Operation Display

When multiple operations run concurrently, the status bar shows `[N ops] Label` with the count and most recently updated operation's label.

## Related Documentation

- [TUI Streaming Output](streaming-output.md) — Cross-thread UI update patterns, ANSI stripping
- [Filter Pipeline](filter-pipeline.md) — Another TUI state management pattern

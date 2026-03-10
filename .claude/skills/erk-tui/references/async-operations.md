---
name: erk-tui-async-operations
description: Streaming output, subprocess management, multi-op tracking, async state snapshots
---

# TUI Async Operations

**Read this when**: Adding background operations, streaming subprocess output, or implementing multi-operation tracking.

## @work(thread=True) Pattern

The standard pattern for background operations:

```python
@work(thread=True)
def _execute_command(self, plan_id: int) -> None:
    try:
        result = subprocess.run(...)
        self.call_from_thread(self.notify, f"Done: {plan_id}")
        self.call_from_thread(self.action_refresh)
    except Exception as e:
        self.call_from_thread(self.notify, f"Error: {e}", severity="error")
```

**Critical rules**:

- ALL UI updates from `@work` threads MUST use `call_from_thread()`
- Direct widget calls from background threads cause silent UI corruption
- Use `run_worker(exclusive=True)` to cancel previous workers before starting new ones
- Match base class signature when overriding Screen actions — if base is async, override must be async too

## call_from_thread() Details

`call_from_thread()` is an **App-level** method, NOT a Widget method. When updating widgets from a background thread, store a reference to the app:

```python
# In a widget's @work method:
self.app.call_from_thread(self._update_display, new_data)
```

## Streaming Subprocess Output

For real-time output visibility in the TUI:

```python
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,  # CRITICAL: prevent deadlock
    bufsize=1,                 # Line-buffered
    text=True,
)
```

**Critical settings**:

- `stdin=subprocess.DEVNULL`: Child processes inherit TUI's stdin. Without this, prompts cause deadlocks.
- `bufsize=1` with `text=True`: Enables line-by-line streaming. Without it, output is block-buffered.
- `stderr=subprocess.STDOUT`: Merge streams for unified output display.

**ANSI handling**: Use `click.unstyle()` to strip ANSI codes before displaying in plain text widgets. Raw ANSI codes render as garbage.

**Error extraction**: On failure, extract the last non-empty output line as the error message.

## Subprocess Feedback Pattern

Beyond exit code, inspect output for success markers:

```python
if return_code == 0:
    if "Updated dispatch metadata" in stderr_output:
        notify("Success", timeout=3)
    else:
        notify("Completed (no changes)", timeout=3)
else:
    last_line = extract_last_nonempty_line(output)
    notify(f"Error: {last_line}", severity="error", timeout=5)
    call_from_thread(self.action_refresh)
```

Exit code 0 alone doesn't distinguish success from silent no-op.

## Multi-Operation Tracking

Track concurrent background operations in the status bar.

**Op ID convention**: `f"{action}-{resource_type}-{resource_id}"` (e.g., `"land-pr-456"`, `"close-plan-123"`)

**Lifecycle**:

1. `start_operation(op_id, description)` — registers in status bar
2. Execute work
3. `finish_operation(op_id)` — removes from status bar

**Critical rule**: Call `finish_operation()` in BOTH success and error paths. Use try/finally:

```python
op_id = f"land-pr-{pr_number}"
self.call_from_thread(self.start_operation, op_id, f"Landing PR #{pr_number}")
try:
    result = subprocess.run(...)
    self.call_from_thread(self.notify, "Landed!")
finally:
    self.call_from_thread(self.finish_operation, op_id)
```

Missing finish calls leave ghost operations in the status bar.

**Preferred runner**: Use `_run_streaming_operation()` for TUI commands. `subprocess.run()` blocks without streaming and produces no status bar updates.

## Async State Snapshot

When an async fetch is in progress and the user switches tabs, fetched data could apply to the wrong view.

**Guard pattern**:

```python
async def _load_data(self) -> None:
    fetched_mode = self._view_mode  # Snapshot at fetch start
    data = await self._provider.fetch(...)

    # Cache under fetched_mode (always correct)
    self._data_cache[fetched_mode.labels] = data

    # Only update display if view hasn't changed
    if fetched_mode == self._view_mode:
        self._update_table(data)
```

**Why**: Without snapshotting, tab-switching during fetch corrupts the display by rendering data for the wrong view.

## action_refresh() After Completion

**Rule**: Always call `call_from_thread(self.action_refresh)` after successful background work. Without it, the TUI shows stale data until the user manually refreshes.

**Never pass `--no-wait` in worker threads** — it defeats the polling purpose. The thread exists to wait for the operation to complete before refreshing.

## Approved EAFP Exception

`@work(thread=True)` workers are the ONE place where try/except for error boundaries is approved (normally erk uses LBYL). The error boundary catches unexpected failures and reports them to the UI via `call_from_thread()` instead of crashing silently.

## Source Documents

Distilled from: `tui/streaming-output`, `tui/subprocess-feedback`, `tui/multi-operation-tracking`, `tui/async-action-refresh-pattern`, `tui/async-state-snapshot`, `tui/textual-async`

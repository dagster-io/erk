---
title: Modal Streaming Command Pattern
read_when:
  - "adding a new long-running CLI operation to the TUI"
  - "working with PlanDetailScreen or CommandOutputPanel"
  - "implementing real-time subprocess output in TUI modals"
  - "debugging thread safety issues in Textual widgets"
tripwires:
  - action: "mutating TUI widgets from a background thread without call_from_thread()"
    warning: "Cross-thread widget mutations cause silent UI corruption. Always use app.call_from_thread()."
last_audited: "2026-02-19 00:00 PT"
audit_result: clean
---

# Modal Streaming Command Pattern

Long-running CLI operations (land PR, submit to queue) need real-time output visibility in the TUI. The streaming command pattern provides this through `PlanDetailScreen.run_streaming_command()`.

## Pattern Overview

1. `PlanDetailScreen.run_streaming_command()` mounts a `CommandOutputPanel` into the detail dialog
2. A subprocess runs in a background worker thread via `_stream_subprocess()`
3. Output is streamed line-by-line to the panel
4. An optional `on_success` callback fires via `app.call_from_thread()` on `returncode == 0`

<!-- Source: src/erk/tui/screens/plan_detail_screen.py, run_streaming_command -->

See `run_streaming_command()` in `src/erk/tui/screens/plan_detail_screen.py:395-426`.

## Method Signature

```python
def run_streaming_command(
    self,
    command: list[str],
    cwd: Path,
    title: str,
    *,
    timeout: float = 30.0,
    on_success: Callable[[], None] | None = None,
) -> None:
```

## Timeouts

| Operation       | Timeout |
| --------------- | ------- |
| Land PR         | 600s    |
| Submit to Queue | 120s    |

Set `timeout=0` to disable the timeout entirely.

## Thread Safety

All widget mutations from background threads **MUST** go through `app.call_from_thread()`. The streaming subprocess runs in a worker thread, so any UI updates triggered by process completion (success callbacks, status changes) must be dispatched to the main thread.

**Anti-pattern:**

```python
# WRONG: Direct widget mutation from background thread
def on_process_done(self):
    self.query_one("#status").update("Done")  # Silent corruption
```

**Correct pattern:**

```python
# RIGHT: Dispatch to main thread
def on_process_done(self):
    self.app.call_from_thread(
        lambda: self.query_one("#status").update("Done")
    )
```

## Callback Mechanism

The `on_success` callback is invoked only when `returncode == 0`. It is called via `app.call_from_thread()` to ensure thread safety. Common use: triggering data refresh or objective updates after a successful land.

<!-- Source: src/erk/tui/app.py, _push_streaming_detail -->

See `_push_streaming_detail()` in `src/erk/tui/app.py:519-558` for how the app pushes a detail screen and schedules the streaming command via `call_after_refresh()`.

## Testing

Use the `_CapturingPlanDetailScreen` test double pattern instead of mocking the full worker/subprocess machinery:

```python
class _CapturingPlanDetailScreen(PlanDetailScreen):
    """Captures on_success callback instead of running a subprocess."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.captured_on_success: Callable[[], None] | None = None

    def run_streaming_command(
        self, command, cwd, title, *, timeout=30.0, on_success=None
    ) -> None:
        self.captured_on_success = on_success
```

This reduces test complexity from ~475 lines (with full worker mocking) to ~80 lines.

<!-- Source: tests/tui/commands/test_execute_command.py, _CapturingPlanDetailScreen -->

See `_CapturingPlanDetailScreen` in `tests/tui/commands/test_execute_command.py:13`.

## Related Topics

- [Dual ABC Callback Injection](../architecture/dual-abc-callback-injection.md) - How CommandExecutor and PlanDataProvider bridge via lambda injection

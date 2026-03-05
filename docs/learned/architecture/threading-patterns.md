---
title: Threading Patterns for Background Operations
read_when:
  - "running blocking operations (subprocess, network) while yielding progress events"
  - "implementing daemon threads for long-running tasks"
  - "understanding the result holder + error holder pattern"
  - "testing code that uses background threads"
---

# Threading Patterns for Background Operations

When a generator-based operation needs to yield progress while a blocking call (e.g., Claude CLI subprocess) is running, erk uses a daemon thread + holder list pattern.

## The Pattern

<!-- Source: src/erk/core/commit_message_generator.py, CommitMessageGenerator.generate -->

See `CommitMessageGenerator.generate()` in `src/erk/core/commit_message_generator.py` for the reference implementation. The method demonstrates the full pattern: holder list setup, daemon thread launch, polling loop with progress ticks, and error checking after join.

### Key Design Decisions

**Holder lists, not variables**: Python closures can't rebind outer variables (`result = ...` inside a function doesn't update the outer `result`). Using `list.append()` sidesteps this without needing `nonlocal`. A list also gives clean LBYL checks (`if error_holder:` vs `if error is not None:`).

**Daemon thread**: `daemon=True` ensures the thread doesn't block process exit if the main thread finishes first (e.g., user presses Ctrl+C). The generator catches errors via the holder pattern, so daemon status doesn't cause data loss for normal completions.

**Polling with timeout**: `thread.join(timeout=_PROGRESS_INTERVAL_SECONDS)` combines waiting and timeout into a single call. Check `thread.is_alive()` after join to distinguish "timed out" from "completed". This avoids a separate timer and produces regular progress ticks.

**Time abstraction**: Use `self._time.monotonic()` rather than `time.monotonic()` directly. This makes elapsed time testable without `sleep()`. The `Time` ABC is in `erk_shared.gateway.time.abc`.

## Thread-Safe Communication

The holder list pattern provides implicit thread safety for single writes:

- Thread writes exactly once (one `append()` call per holder)
- Main thread reads after `thread.join()` confirms completion
- No concurrent reads/writes occur

For more complex state, use `threading.Event` or `queue.Queue`. The commit message pattern is intentionally minimal — it doesn't need a queue because the result is a single value.

## Integration with ProgressEvent

The threading pattern integrates naturally with the [Claude CLI Progress Feedback Pattern](claude-cli-progress.md):

1. Background thread runs the blocking operation
2. Main thread yields `ProgressEvent` ticks during `join(timeout=...)`
3. After thread completes, main thread yields `CompletionEvent` with the result

The generator-based outer function handles all ProgressEvent/CompletionEvent routing; the thread only handles the blocking subprocess call.

## Thread vs. Alternatives

| Approach             | Use When                                                       |
| -------------------- | -------------------------------------------------------------- |
| `threading.Thread`   | Single blocking call, need progress ticks, simple result       |
| `ThreadPoolExecutor` | Multiple parallel tasks, need futures/cancellation             |
| Textual `run_worker` | Inside a Textual app widget; auto-posts messages to event loop |

In erk's generator pipeline, `threading.Thread` is the right choice because:

- There's one blocking operation per generator invocation
- The caller is a synchronous generator (not async, not Textual)
- Progress ticks are simple strings, not structured messages

## Testing

To test threaded generators, consume them synchronously and assert on collected events:

```python
def test_progress_ticks_emitted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Use a slow fake time to make the test deterministic
    fake_time = FakeTime(start=0.0, increment=5.0)  # 5s per call
    generator = CommitMessageGenerator(executor=fake_executor, time=fake_time, ...)

    progress_events: list[ProgressEvent] = []
    result: CommitMessageResult | None = None

    for event in generator.generate(request):
        if isinstance(event, ProgressEvent):
            progress_events.append(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    assert result is not None
    assert any("Still waiting" in e.message for e in progress_events)
```

The `Time` abstraction is critical here — without it, tests would need actual `sleep()` calls to trigger progress ticks.

## Related Documentation

- [Claude CLI Progress Feedback Pattern](claude-cli-progress.md) — ProgressEvent/CompletionEvent architecture
- `src/erk/core/commit_message_generator.py` — Reference implementation of this pattern
- `packages/erk-shared/src/erk_shared/gateway/time/abc.py` — Time abstraction for testability

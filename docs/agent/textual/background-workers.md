---
title: Textual Background Workers
read_when:
  - "running subprocess in TUI without blocking"
  - "streaming output to Textual widgets"
  - "using run_worker for async operations"
---

# Textual Background Workers

## When to Use `run_worker()`

Use `run_worker()` for I/O-bound operations that should not block the UI:

- Subprocess execution with output streaming
- Network requests
- File operations on large files

## Subprocess Streaming Pattern

```python
from textual.worker import Worker, WorkerState
import asyncio

def action_execute(self) -> None:
    """Start command execution."""
    self._output_panel.visible = True
    self.run_worker(self._stream_subprocess, exclusive=True)

async def _stream_subprocess(self) -> None:
    """Run subprocess and stream output to widget."""
    proc = await asyncio.create_subprocess_exec(
        "command", "arg1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async for line in proc.stdout:
        # call_from_thread updates UI safely from worker
        self.call_from_thread(self._append_output, line.decode())

    await proc.wait()
    self.call_from_thread(self._on_complete, proc.returncode)
```

## Key Points

- `exclusive=True` cancels any running worker before starting new one
- Use `call_from_thread()` to update widgets from worker context
- Worker state can be checked via `worker.state`
- Workers run in a thread pool, not the main asyncio loop

## Testing Workers

Workers are difficult to test in isolation. For testable subprocess execution:

- Keep subprocess logic in the worker method
- Test UI state changes via Pilot API
- Consider integration tests for full workflow

See [testing.md](testing.md) for TUI testing patterns.

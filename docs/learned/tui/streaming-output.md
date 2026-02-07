---
title: TUI Streaming Output Patterns
read_when:
  - "displaying streaming command output in TUI"
  - "executing long-running commands with progress"
  - "cross-thread UI updates in Textual"
---

# TUI Streaming Output Patterns

This guide covers patterns for displaying streaming command output in the Erk TUI without blocking the UI thread.

## Overview

When executing long-running commands (like `submit_to_queue`), you want to:

- Show real-time output to the user
- Keep the UI responsive
- Handle subprocess communication safely across threads

## Architecture Pattern

### Components

1. **Process Manager** - Manages subprocess and reads output in background thread
2. **Event Queue** - Collects parsed output events from background thread
3. **Output Widget** - Displays streaming content in UI
4. **Cross-Thread Updates** - Uses `app.call_from_thread()` to update UI safely

### Example: ClaudeProcess Pattern

```python
import subprocess
import threading
from queue import Queue
from typing import Optional

from textual.app import App

class ClaudeProcess:
    """Manages subprocess execution with streaming output."""

    def __init__(self, app: App):
        self._app = app
        self._process: Optional[subprocess.Popen] = None
        self._events: Queue[StreamEvent] = Queue()
        self._reader_thread: Optional[threading.Thread] = None

    def start(self, command: list[str]) -> None:
        """Start subprocess with background reader thread."""
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )

        # Background thread reads stdout
        self._reader_thread = threading.Thread(
            target=self._read_output,
            daemon=True
        )
        self._reader_thread.start()

    def _read_output(self) -> None:
        """Read subprocess output (runs in background thread)."""
        assert self._process and self._process.stdout

        for line in self._process.stdout:
            event = parse_stream_event(line)
            self._events.put(event)

            # Update UI from background thread
            self._app.call_from_thread(self._handle_event, event)

    def _handle_event(self, event: StreamEvent) -> None:
        """Handle event (runs in main thread via call_from_thread)."""
        # Safe to update UI here
        output_widget = self._app.query_one("#output", CommandOutputPanel)
        output_widget.append_line(event.text)
```

## Critical: Threading Safety

**WRONG** ❌

```python
class MyWidget(Widget):
    def update_from_thread(self):
        # BAD: self.call_from_thread is not available
        self.call_from_thread(self._update_ui)
```

**CORRECT** ✅

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

## Stream Event Parsing

For JSON-based streaming formats (like Claude CLI):

```python
from dataclasses import dataclass
import json

@dataclass
class StreamEvent:
    event_type: str
    text: str
    metadata: dict

def parse_stream_event(line: str) -> StreamEvent:
    """Parse JSON-based stream events."""
    try:
        data = json.loads(line)
        return StreamEvent(
            event_type=data.get("type", "unknown"),
            text=data.get("content", ""),
            metadata=data
        )
    except json.JSONDecodeError:
        # Fallback: treat as plain text
        return StreamEvent(
            event_type="text",
            text=line.strip(),
            metadata={}
        )
```

## Widget Selection for Streaming Output

| Widget    | Use When                   | Max Lines          | Auto-Scroll |
| --------- | -------------------------- | ------------------ | ----------- |
| `Log`     | Simple line-by-line output | Yes (configurable) | Yes         |
| `RichLog` | Rich text with markup      | Yes (configurable) | Yes         |
| `Static`  | Small, static content      | No limit           | No          |

**For streaming command output, use `Log` or `RichLog`:**

```python
from textual.widgets import Log

class CommandOutputPanel(Static):
    def compose(self) -> ComposeResult:
        yield Log(
            max_lines=1000,  # Limit memory usage
            auto_scroll=True  # Follow output
        )

    def append_line(self, text: str) -> None:
        """Add line to output (call from main thread only)."""
        log = self.query_one(Log)
        log.write_line(text)
```

## Modal Dismiss Blocking

Prevent users from dismissing modals while commands are running:

```python
from textual.screen import Screen

class CommandRunnerScreen(Screen):
    def __init__(self):
        super().__init__()
        self._command_running = False

    async def action_dismiss(self) -> None:
        """Override to block dismiss while command runs."""
        if self._command_running:
            # Silently ignore dismiss attempts
            return

        # Normal dismiss when not running
        await super().action_dismiss()

    async def execute_command(self, cmd: str) -> None:
        """Execute command with dismiss blocking."""
        self._command_running = True
        try:
            # Run command...
            await self._run_subprocess(cmd)
        finally:
            self._command_running = False
```

## Related Documentation

- [Textual Async Best Practices](textual-async.md)
- [Command Execution Strategies](../architecture/command-execution.md)

---
title: LiveDisplay Gateway
read_when:
  - "implementing live-updating terminal displays"
  - "working with TUI real-time updates"
  - "showing progress indicators"
---

# LiveDisplay Gateway

Gateway abstraction for live-updating terminal displays. Provides interface for showing real-time progress and status updates in the TUI.

## Overview

**Location:** `packages/erk-shared/src/erk_shared/gateway/live_display/`

**Purpose:** Abstracts Rich's `Live` display functionality for testability and clean separation from business logic.

**Key Design:** Simple 3-method interface (start, update, stop) that wraps Rich's live rendering.

## Architecture

The gateway follows the standard 3-file pattern:

- `abc.py` - Abstract interface
- `real.py` - Production implementation using Rich Live
- `fake.py` - In-memory test implementation with message capture

## Interface

### start() -> None

Start live display mode. Begins capturing terminal updates.

### update(renderable: RenderableType) -> None

Update the display with new content.

**Args:**

- `renderable`: Any Rich renderable object (Text, Table, Panel, etc.)

### stop() -> None

Stop live display mode. Returns terminal to normal output.

## Usage Pattern

```python
def run_with_progress(ctx: ErkContext) -> None:
    display = ctx.live_display

    display.start()
    try:
        for step in steps:
            # Update display with current progress
            display.update(create_progress_table(step))
            perform_work(step)
    finally:
        display.stop()
```

## Fake Features

`FakeLiveDisplay` provides:

- **Display call tracking** - Records start/stop calls
- **Message capture** - Captures all `update()` calls for test assertions
- **No actual rendering** - Tests run without terminal output

## When to Use

Use `ctx.live_display` when:

- Showing live progress during long operations
- Updating status displays in real-time
- Implementing TUI components with dynamic content

Don't use for:

- Static output (use `Console` or `print()` instead)
- Single updates (not worth the start/stop overhead)
- Non-interactive commands (waste of rendering resources)

## Related Topics

- [Gateway Inventory](gateway-inventory.md) - All available gateways
- [Console Gateway](gateway-inventory.md#console-consoleconsole) - For static output
- [Textual Framework](../textual/) - For full TUI applications

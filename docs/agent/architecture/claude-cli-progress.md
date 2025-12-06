---
title: Claude CLI Progress Feedback Pattern
read_when:
  - "adding progress output to Claude operations"
  - "wrapping Claude CLI with user feedback"
  - "using ProgressEvent or CompletionEvent"
  - "converting blocking operations to streaming progress"
---

# Claude CLI Progress Feedback Pattern

When wrapping Claude CLI operations, use the generator-based event pattern to provide real-time progress feedback to users.

## Core Components

### ProgressEvent

A frozen dataclass for progress notifications during operations:

```python
from erk_shared.integrations.gt.events import ProgressEvent

# Basic progress
yield ProgressEvent("Reading diff file...")

# Styled progress (success, warning, error)
yield ProgressEvent("Diff loaded (1,234 chars)", style="success")
yield ProgressEvent("PR has merge conflicts", style="warning")
```

**Styles**: `"info"` (default), `"success"`, `"warning"`, `"error"`

### CompletionEvent

A frozen dataclass wrapping the final result:

```python
from erk_shared.integrations.gt.events import CompletionEvent

# Return result via CompletionEvent
yield CompletionEvent(MyResult(success=True, data=data))
```

## Pattern: Generator-Based Operations

Convert blocking operations to generators that yield progress:

```python
from collections.abc import Generator
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent

def my_operation(
    request: MyRequest,
) -> Generator[ProgressEvent | CompletionEvent[MyResult]]:
    """Operation with progress updates.

    Yields:
        ProgressEvent for status updates
        CompletionEvent with result on completion
    """
    yield ProgressEvent("Starting operation...")

    # Do work
    yield ProgressEvent("Processing...", style="info")
    result = do_expensive_work()

    yield ProgressEvent("Complete", style="success")
    yield CompletionEvent(MyResult(success=True, data=result))
```

## Pattern: Consuming Generator Results

CLI commands consume the generator, render progress, and extract the result:

```python
def _run_operation(
    request: MyRequest,
    debug: bool,
) -> MyResult:
    """Run operation and return result."""
    result: MyResult | None = None

    for event in my_operation(request):
        if isinstance(event, ProgressEvent):
            _render_progress(event)  # Always show, or gate with `if debug:`
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return MyResult(success=False, error="Operation did not complete")

    return result


def _render_progress(event: ProgressEvent) -> None:
    """Render a progress event to the CLI."""
    style_map = {
        "info": {"dim": True},
        "success": {"fg": "green"},
        "warning": {"fg": "yellow"},
        "error": {"fg": "red"},
    }
    style = style_map.get(event.style, {})
    click.echo(click.style(f"   {event.message}", **style))
```

## Pattern: Testing Generator Operations

Use a helper to consume generators in tests:

```python
def _consume_generator(
    generator: MyGenerator, request: MyRequest
) -> tuple[MyResult, list[ProgressEvent]]:
    """Consume generator and return result with collected progress events."""
    progress_events: list[ProgressEvent] = []
    result: MyResult | None = None

    for event in generator.generate(request):
        if isinstance(event, ProgressEvent):
            progress_events.append(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        raise AssertionError("Generator did not yield CompletionEvent")

    return result, progress_events


def test_operation_emits_progress(tmp_path: Path) -> None:
    result, progress_events = _consume_generator(generator, request)

    assert result.success is True
    assert any("Processing" in e.message for e in progress_events)
    assert any(e.style == "success" for e in progress_events)
```

## Example: CommitMessageGenerator

Real example from `src/erk/core/commit_message_generator.py`:

```python
def generate(
    self, request: CommitMessageRequest
) -> Generator[ProgressEvent | CompletionEvent[CommitMessageResult]]:
    yield ProgressEvent("Reading diff file...")

    if not request.diff_file.exists():
        yield CompletionEvent(CommitMessageResult(
            success=False, error_message="Diff file not found"
        ))
        return

    diff_content = request.diff_file.read_text()
    yield ProgressEvent(f"Diff loaded ({len(diff_content):,} chars)", style="success")

    yield ProgressEvent("Analyzing changes with Claude...")
    result = self._executor.execute_prompt(prompt, model=self._model)

    if not result.success:
        yield CompletionEvent(CommitMessageResult(
            success=False, error_message=result.error
        ))
        return

    yield ProgressEvent("PR description generated", style="success")
    yield CompletionEvent(CommitMessageResult(
        success=True, title=title, body=body
    ))
```

## When to Use This Pattern

Use generator-based progress when:

- Operation takes > 1 second (Claude CLI calls)
- Multiple distinct phases users should see
- You want testable progress assertions

Skip for:

- Fast operations (< 1 second)
- Operations with no meaningful intermediate states

## Pattern: Typed Claude CLI Events

For consuming Claude CLI streaming output directly, use the typed `ClaudeEvent` union:

```python
from erk.core.claude_executor import (
    ClaudeEvent,
    ErrorEvent,
    PrNumberEvent,
    SpinnerUpdateEvent,
    TextEvent,
    ToolEvent,
)

for event in executor.execute_command_streaming(...):
    match event:
        case TextEvent(content=text):
            print(text)
        case ToolEvent(summary=summary):
            print(f"  > {summary}")
        case SpinnerUpdateEvent(status=status):
            print(f"  ... {status}")
        case PrNumberEvent(number=num):
            pr_number = num  # Already int, no conversion needed
        case ErrorEvent(message=msg):
            handle_error(msg)
```

**Key Benefits**:

- **Type safety**: Pattern matching with exhaustiveness checking
- **No string conversion**: `PrNumberEvent.number` and `IssueNumberEvent.number` are proper `int`
- **Self-documenting**: `PrUrlEvent(url=...)` vs stringly-typed events
- **IDE support**: Autocomplete and refactoring work correctly

**See also**: [Glossary - ClaudeEvent](../glossary.md#claudeevent) for complete event type reference.

## Related Files

- `packages/erk-shared/src/erk_shared/integrations/gt/events.py` - ProgressEvent/CompletionEvent definitions
- `src/erk/core/claude_executor.py` - ClaudeEvent definitions
- `packages/erk-shared/src/erk_shared/integrations/gt/operations/` - Example operations
- `src/erk/cli/commands/pr/submit_cmd.py` - CLI consumption example

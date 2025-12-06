---
title: Event-Based Progress Pattern
read_when:
  - "implementing operations that need progress reporting"
  - "separating business logic from UI output"
  - "building testable CLI operations"
  - "using ProgressEvent or CompletionEvent"
---

# Event-Based Progress Pattern

This document describes the generator-based event pattern used for operations that need progress reporting while keeping business logic testable and UI-agnostic.

## Overview

Operations yield events instead of using `click.echo()` directly. This enables:

1. **Pure business logic** - No CLI dependencies in operation code
2. **Testable progress assertions** - Tests can verify exact progress sequence
3. **Flexible rendering** - CLI, JSON, or silent modes without code changes

## Core Event Types

Located in `packages/erk-shared/src/erk_shared/integrations/gt/events.py`:

### ProgressEvent

Notification during operation execution:

```python
@dataclass(frozen=True)
class ProgressEvent:
    """Progress notification during operation.

    Attributes:
        message: Human-readable progress message
        style: Visual style hint for rendering
    """
    message: str
    style: Literal["info", "success", "warning", "error"] = "info"
```

### CompletionEvent

Final result yielded as the last event:

```python
@dataclass(frozen=True)
class CompletionEvent[T]:
    """Final result of an operation.

    Attributes:
        result: The operation result (success or error dataclass)
    """
    result: T
```

## Generator-Based Pattern

Operations are generators that yield progress events, then yield a completion event:

```python
def execute_operation(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[SuccessType | ErrorType]]:
    """Execute operation with progress reporting.

    Yields:
        ProgressEvent for status updates
        CompletionEvent with SuccessType or ErrorType as final event
    """
    # Step 1: Report progress
    yield ProgressEvent("Starting operation...")

    # Step 2: Do work
    result = do_something(ops, cwd)

    # Step 3: Report more progress
    if result.has_issues:
        yield ProgressEvent(f"Found {len(result.issues)} issue(s)", style="warning")
    else:
        yield ProgressEvent("Operation completed successfully", style="success")

    # Step 4: Yield final result
    yield CompletionEvent(
        SuccessType(
            success=True,
            message="Operation completed",
            data=result.data,
        )
    )
```

## Consuming Events

### CLI Layer - render_events() Helper

The CLI layer consumes events and renders them appropriately:

```python
from erk.cli.output import render_events

def run_command(ctx: ErkContext) -> None:
    for event in execute_operation(ctx.gt_kit, ctx.cwd):
        if isinstance(event, ProgressEvent):
            render_events(event)  # Renders to stderr with styling
        elif isinstance(event, CompletionEvent):
            result = event.result
            if result.success:
                click.echo(f"Done: {result.message}")
            else:
                raise click.ClickException(result.message)
```

### Testing - Collect and Assert

Tests collect events and verify the sequence:

```python
def test_operation_progress() -> None:
    fake_ops = create_fake_gt_kit()

    events = list(execute_operation(fake_ops, Path("/repo")))

    # Verify progress events
    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    assert len(progress_events) == 2
    assert progress_events[0].message == "Starting operation..."
    assert progress_events[1].style == "success"

    # Verify completion
    completion = events[-1]
    assert isinstance(completion, CompletionEvent)
    assert completion.result.success is True
```

## Composing Operations

Operations can delegate to other operations by yielding their events:

```python
def execute_composite_operation(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[CompositeResult | CompositeError]]:
    """Composite operation that delegates to sub-operations."""

    # Delegate to sub-operation, forwarding its progress events
    yield ProgressEvent("Running sub-operation...")
    for event in execute_sub_operation(ops, cwd):
        if isinstance(event, CompletionEvent):
            # Handle sub-operation result
            sub_result = event.result
            if not sub_result.success:
                yield CompletionEvent(
                    CompositeError(
                        success=False,
                        error_type="sub_operation_failed",
                        message=sub_result.message,
                    )
                )
                return
            # Continue with sub_result.data
        else:
            # Forward progress events
            yield event

    # Continue with composite operation...
    yield CompletionEvent(
        CompositeResult(success=True, message="Composite operation complete")
    )
```

## Benefits

### Testable

Business logic tests don't need to mock `click.echo()`:

```python
# WRONG: Testing with mocked click
@patch("click.echo")
def test_operation(mock_echo):
    run_operation()
    mock_echo.assert_called_with("Progress...")  # Brittle

# RIGHT: Testing with events
def test_operation():
    events = list(execute_operation(fake_ops, path))
    assert events[0].message == "Progress..."  # Direct assertion
```

### Composable

Operations can be combined without output conflicts:

```python
# Each sub-operation yields its own events
# Parent operation decides which to forward
for event in sub_operation():
    if should_forward(event):
        yield event
```

### UI-Agnostic

Same operation works for CLI, JSON API, or silent batch:

```python
# CLI mode - render with colors
for event in operation():
    render_event(event, use_colors=True)

# JSON mode - collect and serialize
events = list(operation())
print(json.dumps([e.to_dict() for e in events]))

# Silent mode - ignore progress
for event in operation():
    if isinstance(event, CompletionEvent):
        return event.result
```

## Real-World Example

From restack preflight (`restack_preflight.py`):

```python
def execute_restack_preflight(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[RestackPreflightSuccess | RestackPreflightError]]:
    """Execute restack preflight: squash + restack attempt + detect conflicts."""

    branch_name = ops.git.get_current_branch(cwd) or "unknown"

    # Step 1: Squash commits (delegate to squash operation)
    yield ProgressEvent("Squashing commits...")
    for event in execute_squash(ops, cwd):
        if isinstance(event, CompletionEvent):
            result = event.result
            if isinstance(result, SquashError):
                yield CompletionEvent(
                    RestackPreflightError(
                        success=False,
                        error_type="squash_failed",
                        message=result.message,
                    )
                )
                return
        else:
            yield event  # Forward squash progress

    # Step 2: Attempt restack
    yield ProgressEvent("Running gt restack...")
    try:
        ops.graphite.restack(repo_root, no_interactive=True, quiet=True)
    except subprocess.CalledProcessError:
        pass  # Expected if conflicts

    # Step 3: Check for conflicts
    if ops.git.is_rebase_in_progress(cwd):
        conflicts = ops.git.get_conflicted_files(cwd)
        yield ProgressEvent(f"Found {len(conflicts)} conflict(s)", style="warning")
        yield CompletionEvent(
            RestackPreflightSuccess(
                success=True,
                has_conflicts=True,
                conflicts=conflicts,
                branch_name=branch_name,
                message=f"{len(conflicts)} conflict(s) detected",
            )
        )
    else:
        yield ProgressEvent("Restack completed successfully", style="success")
        yield CompletionEvent(
            RestackPreflightSuccess(
                success=True,
                has_conflicts=False,
                conflicts=[],
                branch_name=branch_name,
                message="Restack completed successfully",
            )
        )
```

## Related Documentation

- [Three-Phase Restack Architecture](restack-operations.md) - Uses this pattern
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection context

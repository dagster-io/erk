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

## Multi-Phase Pipelines

Complex operations often chain multiple generator-based phases together, with data flowing through typed results. Each phase consumes data from previous phases and produces new data for subsequent phases.

### Pipeline Structure

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Preflight     │────▶│  Commit Message  │────▶│   Finalize     │
│                 │     │    Generator     │     │                │
└─────────────────┘     └──────────────────┘     └────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
 PreflightResult         CommitMessageResult     FinalizeResult
 - pr_number             - title                 - pr_url
 - diff_file             - body                  - graphite_url
 - commit_messages ──────▶ (consumed)
```

### Data Flow Pattern

Multi-phase pipelines follow this structure:

1. **Phase 1 (Preflight)**: Collects all data needed by subsequent phases
   - Captures data before any destructive operations (see [Pre-Destruction Capture](pre-destruction-capture.md))
   - Returns typed result with all collected data
   - Yields progress events during data collection

2. **Phase 2 (Generation)**: Consumes data from Phase 1, produces transformations
   - Takes request type with fields from Phase 1 result
   - Performs expensive operations (AI generation, complex computation)
   - Returns typed result with generated content
   - Yields progress events during generation

3. **Phase 3 (Finalize)**: Applies transformations using data from both prior phases
   - Takes results from Phase 1 and Phase 2
   - Performs final mutations (create PR, commit changes, etc.)
   - Returns final result
   - Yields progress events during finalization

### Real-World Example: PR Submit Pipeline

From `erk pr submit`:

```python
# Phase 1: Preflight - collect data before mutations
def run_preflight_phase(
    ops: GtKit,
    options: SubmitOptions,
) -> Generator[ProgressEvent | CompletionEvent[PreflightResult | PreflightError]]:
    """Collect all data needed for PR creation."""

    yield ProgressEvent("Running preflight checks...")

    parent_branch = ops.graphite.get_parent_branch(ops.cwd)

    # CRITICAL: Capture commit messages BEFORE squashing
    # (see Pre-Destruction Capture pattern)
    commit_messages = ops.git.get_commit_messages_since(ops.cwd, parent_branch)

    # Squash commits (destructive operation)
    yield ProgressEvent("Squashing commits...")
    squash_commits(ops.git, ops.cwd, parent_branch)

    # Generate diff for AI
    diff_file = generate_diff(ops.git, ops.cwd, parent_branch)

    yield CompletionEvent(
        PreflightResult(
            success=True,
            parent_branch=parent_branch,
            diff_file=diff_file,
            commit_messages=commit_messages,  # ← Preserved for Phase 2
            pr_number=options.pr_number,
        )
    )

# Phase 2: Generation - produce PR title/body using Phase 1 data
def generate_commit_message(
    ops: GtKit,
    request: CommitMessageRequest,
) -> Generator[ProgressEvent | CompletionEvent[CommitMessageResult | GenerationError]]:
    """Generate PR title and body using AI."""

    yield ProgressEvent("Generating PR description with AI...")

    # Consume data from Phase 1
    prompt = build_prompt(
        diff=request.diff_file.read_text(encoding="utf-8"),
        commit_messages=request.commit_messages,  # ← Consumed from Phase 1
        existing_pr=request.pr_number,
    )

    # Generate with AI
    response = ops.ai.generate(prompt)

    yield ProgressEvent("PR description generated", style="success")

    yield CompletionEvent(
        CommitMessageResult(
            success=True,
            title=response.title,
            body=response.body,
        )
    )

# Phase 3: Finalize - apply results to create/update PR
def finalize_pr_submit(
    ops: GtKit,
    preflight: PreflightResult,
    commit_msg: CommitMessageResult,
    options: SubmitOptions,
) -> Generator[ProgressEvent | CompletionEvent[FinalizeResult | FinalizeError]]:
    """Create or update PR with generated content."""

    yield ProgressEvent("Creating PR...")

    if preflight.pr_number:
        # Update existing PR
        ops.github.update_pr_description(
            preflight.pr_number,
            title=commit_msg.title,
            body=commit_msg.body,
        )
        yield ProgressEvent(f"Updated PR #{preflight.pr_number}", style="success")
    else:
        # Create new PR
        pr_url = ops.github.create_pr(
            title=commit_msg.title,
            body=commit_msg.body,
            base=preflight.parent_branch,
        )
        yield ProgressEvent(f"Created PR: {pr_url}", style="success")

    yield CompletionEvent(
        FinalizeResult(
            success=True,
            pr_url=pr_url,
            graphite_url=ops.graphite.get_stack_url(),
        )
    )

# Top-level orchestration
def execute_pr_submit(
    ops: GtKit,
    options: SubmitOptions,
) -> Generator[ProgressEvent | CompletionEvent[SubmitSuccess | SubmitError]]:
    """Orchestrate all phases of PR submission."""

    # Phase 1: Preflight
    preflight_result = None
    for event in run_preflight_phase(ops, options):
        if isinstance(event, CompletionEvent):
            if not event.result.success:
                yield CompletionEvent(SubmitError(...))
                return
            preflight_result = event.result
        else:
            yield event  # Forward progress

    # Phase 2: Generation
    commit_msg_result = None
    request = CommitMessageRequest(
        diff_file=preflight_result.diff_file,
        commit_messages=preflight_result.commit_messages,  # ← Data flows through
        pr_number=preflight_result.pr_number,
    )
    for event in generate_commit_message(ops, request):
        if isinstance(event, CompletionEvent):
            if not event.result.success:
                yield CompletionEvent(SubmitError(...))
                return
            commit_msg_result = event.result
        else:
            yield event  # Forward progress

    # Phase 3: Finalize
    for event in finalize_pr_submit(ops, preflight_result, commit_msg_result, options):
        if isinstance(event, CompletionEvent):
            if not event.result.success:
                yield CompletionEvent(SubmitError(...))
                return
            # Map to top-level result
            yield CompletionEvent(
                SubmitSuccess(
                    success=True,
                    pr_url=event.result.pr_url,
                    message="PR submitted successfully",
                )
            )
            return
        else:
            yield event  # Forward progress
```

### Key Principles

1. **Each phase's result type contains exactly what downstream phases need**
   - `PreflightResult` has `commit_messages` for Phase 2
   - `CommitMessageResult` has `title` and `body` for Phase 3

2. **Capture before destruction**
   - Phase 1 captures `commit_messages` BEFORE squashing
   - Once squashed, original messages are unrecoverable
   - See [Pre-Destruction Capture Pattern](pre-destruction-capture.md)

3. **Typed request/response**
   - Each phase has explicit input (request) and output (result) types
   - No implicit data passing through global state
   - Type checker verifies data flow correctness

4. **Progress transparency**
   - Each phase yields progress events
   - Top-level orchestrator forwards events to CLI
   - Tests can verify progress sequence for each phase

5. **Error propagation**
   - If any phase fails, entire pipeline stops
   - Error from Phase 1 prevents Phase 2 from running
   - Clean error handling at each boundary

### When to Use Multi-Phase Pipelines

Use this pattern when:

- Operation has distinct conceptual stages (collect → transform → apply)
- Early phases must capture data before later phases destroy it
- Expensive operations (AI, I/O) should be separated for testing
- Each phase can fail independently
- Progress reporting needed for long-running operations

### Testing Multi-Phase Pipelines

Test each phase independently:

```python
def test_preflight_preserves_commit_messages():
    """Test Phase 1 captures commit messages before squashing."""
    fake_git = FakeGit(
        commit_messages_since={(Path("/repo"), "main"): ["feat: add X", "fix: bug Y"]}
    )
    fake_ops = create_fake_gt_kit(git=fake_git)

    events = list(run_preflight_phase(fake_ops, options))
    completion = events[-1]

    assert isinstance(completion, CompletionEvent)
    assert completion.result.commit_messages == ["feat: add X", "fix: bug Y"]


def test_generation_consumes_preflight_data():
    """Test Phase 2 uses data from Phase 1."""
    request = CommitMessageRequest(
        diff_file=Path("/tmp/diff.txt"),
        commit_messages=["feat: add X", "fix: bug Y"],  # From Phase 1
        pr_number=None,
    )

    events = list(generate_commit_message(fake_ops, request))
    completion = events[-1]

    assert isinstance(completion, CompletionEvent)
    assert "feat: add X" in completion.result.body  # Used commit messages
```

Test orchestration separately:

```python
def test_pr_submit_pipeline_end_to_end():
    """Test full pipeline integration."""
    fake_ops = create_fake_gt_kit_for_pr_submit()

    events = list(execute_pr_submit(fake_ops, options))

    # Verify progress from all phases
    progress = [e for e in events if isinstance(e, ProgressEvent)]
    assert any("preflight" in e.message.lower() for e in progress)
    assert any("generating" in e.message.lower() for e in progress)
    assert any("created pr" in e.message.lower() for e in progress)

    # Verify final result
    completion = events[-1]
    assert isinstance(completion, CompletionEvent)
    assert completion.result.success is True
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
- [Pre-Destruction Capture Pattern](pre-destruction-capture.md) - Critical for multi-phase pipelines
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection context

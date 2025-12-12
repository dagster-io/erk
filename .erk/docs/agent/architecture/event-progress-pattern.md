---
title: Event-Based Progress Pattern
read_when:
  - "implementing operations that need progress reporting"
  - "separating business logic from UI output"
  - "building testable CLI operations"
  - "using ProgressEvent or CompletionEvent"
---

# Event-Based Progress Pattern

Operations yield events instead of using `click.echo()` directly. This enables:

1. **Pure business logic** - No CLI dependencies in operation code
2. **Testable progress assertions** - Tests can verify exact progress sequence
3. **Flexible rendering** - CLI, JSON, or silent modes without code changes

## Source Files

Event types are defined in `packages/erk-shared/src/erk_shared/integrations/gt/events.py`.

For implementation examples, see operations in `packages/erk/src/erk/operations/`.

## Core Event Types

### ProgressEvent

Notification during operation execution. Contains a message and optional style hint (`"info"`, `"success"`, `"warning"`, `"error"`).

### CompletionEvent

Final result yielded as the last event. Contains a typed result object (typically a success or error dataclass).

## Generator-Based Pattern

Operations are generators that:

1. **Yield ProgressEvent** for status updates during execution
2. **Yield CompletionEvent** as the final event with the result

The generator signature returns `Generator[ProgressEvent | CompletionEvent[SuccessType | ErrorType]]`.

## Consuming Events

### CLI Layer

The CLI layer iterates through events:

- For `ProgressEvent`: Render to stderr with styling
- For `CompletionEvent`: Extract result, handle success or raise error

The `render_events()` helper in `erk.cli.output` handles common rendering patterns.

### Testing

Tests collect events into a list and make assertions:

- Filter for `ProgressEvent` to verify progress messages
- Check the final `CompletionEvent` for the result

This avoids mocking `click.echo()` - tests assert on event data directly.

## Composing Operations

Operations can delegate to sub-operations by iterating their events:

- Forward `ProgressEvent` to the caller
- Handle `CompletionEvent` internally to get sub-operation results
- Yield own `CompletionEvent` with final result

## Benefits

### Testable

Business logic tests don't need to mock `click.echo()`. Instead, collect events and assert on their content directly.

### Composable

Operations can be combined without output conflicts. Each sub-operation yields its own events; the parent decides which to forward.

### UI-Agnostic

Same operation works for CLI (render with colors), JSON API (serialize events), or silent batch mode (ignore progress, return result).

## Multi-Phase Pipelines

Complex operations often chain multiple generator-based phases, with data flowing through typed results.

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Preflight     │────▶│   Generation     │────▶│   Finalize     │
│                 │     │                  │     │                │
└─────────────────┘     └──────────────────┘     └────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
 PreflightResult         GenerationResult        FinalizeResult
```

### Data Flow Pattern

1. **Phase 1 (Preflight)**: Collect all data needed by subsequent phases
2. **Phase 2 (Generation)**: Consume Phase 1 data, produce transformation
3. **Phase 3 (Finalize)**: Apply transformations, return final result

**Key principle**: Each phase's result type contains exactly what downstream phases need.

### Orchestrating Multi-Phase Pipelines

The CLI command orchestrates all phases:

1. Run Phase 1, render events, extract result (or fail)
2. Build Phase 2 request from Phase 1 result
3. Run Phase 2, render events, extract result (or fail)
4. Run Phase 3 with Phase 2 result, render events, return final result

See operations like `submit_pr` in the codebase for concrete examples of this pattern.

## Related Documentation

- [Pre-Destruction Data Capture](pre-destruction-capture.md) - Capturing data before mutations
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection context

---
title: Callback Progress Pattern
read_when:
  - "adding progress reporting to operations functions"
  - "choosing between callback and event-based progress"
  - "implementing synchronous progress feedback"
---

# Callback Progress Pattern

For operations that need simple progress reporting without the complexity of event generators, use a callback parameter.

## When to Use This Pattern

Choose callbacks over event generators when:

- Operations are synchronous
- Progress is lightweight (operation names/milestones only)
- Single consumer (typically CLI output)
- No structured event data needed

For complex async operations with multiple event types or structured data, see [Event-Based Progress Pattern](event-progress-pattern.md).

## Implementation Pattern

### Function Signature

Add a callback parameter as keyword-only. See `sync_agent_docs()` in `src/erk/agent_docs/operations.py` for the reference implementation.

Key elements:

- Parameter: `on_progress: Callable[[str], None]`
- Position: Last keyword-only parameter, after all other required parameters
- Import `Callable` from `collections.abc`

### Invocation

Call the callback directly at milestone points:

```python
on_progress("Scanning docs...")
# ... do work ...
on_progress("Generating indexes...")
```

No guard needed since the parameter is always required. Callers that want silence pass a no-op lambda.

### CLI Binding

In CLI commands, bind the callback to styled output:

```python
# sync.py - routes progress to styled stderr
on_progress=lambda msg: click.echo(click.style(msg, fg="cyan"), err=True)
```

### Silent Binding

For commands that don't need visible progress (validation, testing):

```python
# check.py - suppresses progress output
on_progress=lambda _: None
```

### Test Pattern

Pass `on_progress=lambda _: None` in tests to suppress output without mock complexity. Only test callback invocation if specifically testing the progress feature.

## Milestone Granularity

For operations processing many items (>10), use milestone-based progress rather than per-item reporting:

- **<10 items**: Per-item progress acceptable
- **10-100 items**: Use milestones at operation boundaries
- **>100 items**: Consider percentage or count indicators

Example: `erk docs sync` processes ~55 files but reports only 6 milestones (one per pipeline stage).

## Related Documentation

- [Event-Based Progress Pattern](event-progress-pattern.md) - Generator-based alternative for complex operations
- [CLI Output Styling Guide](../cli/output-styling.md) - Progress output conventions

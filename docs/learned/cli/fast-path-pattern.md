---
title: Fast Path Pattern for CLI Commands
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
read_when:
  - "implementing CLI commands that can skip expensive operations"
  - "adding fast path optimization to existing commands"
  - "understanding when to invoke Claude vs complete locally"
---

# Fast Path Pattern for CLI Commands

Some CLI commands can complete without expensive operations (like Claude invocation) when conditions are favorable.

## Pattern Overview

```
┌─────────────────┐
│   Preflight     │──► Check if fast path is possible
└────────┬────────┘
         │
    ┌────┴────┐
    │ Condition │
    │   Met?    │
    └────┬────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Fast Path   Slow Path
(skip AI)   (use AI)
```

## When to Use

Use the fast path pattern when:

- An expensive operation (AI, network, subprocess) can be skipped
- A cheap preflight check can determine if the operation is needed
- The fast path produces the same result as the slow path

## Implementation Example

See `erk pr auto-restack` for a concrete example:

**Fast path:** Restack completes without conflicts → finish immediately
**Slow path:** Conflicts detected → fall back to Claude for resolution

## Key Principles

1. **Preflight first:** Always run cheap checks before expensive operations
2. **Clear messaging:** Tell users which path was taken
3. **Same result:** Both paths should achieve the same outcome
4. **Graceful fallback:** Slow path handles all edge cases

## Related Documentation

- [Event-Based Progress Pattern](../architecture/event-progress-pattern.md) - Progress reporting

---
title: Sessions Documentation
read_when:
  - "analyzing Claude Code sessions"
  - "parsing session logs"
  - "debugging context window issues"
---

# Sessions Documentation

Working with Claude Code session logs and context analysis.

## Quick Navigation

| When you need to...              | Read this                                                      |
| -------------------------------- | -------------------------------------------------------------- |
| Understand session log structure | [layout.md](layout.md)                                         |
| Work with parallel sessions      | [parallel-session-awareness.md](parallel-session-awareness.md) |
| Use session analysis tools       | [tools.md](tools.md)                                           |
| Debug context window issues      | [context-analysis.md](context-analysis.md)                     |

## Documents in This Category

### Session Layout

**File:** [layout.md](layout.md)

Detailed guide to Claude Code session log structure in ~/.claude/projects/, including file formats, message types, and navigation.

### Parallel Session Awareness

**File:** [parallel-session-awareness.md](parallel-session-awareness.md)

Critical patterns for working with session-specific data when multiple Claude sessions run in parallel on the same codebase.

### Session Tools

**File:** [tools.md](tools.md)

Tools and utilities for parsing, analyzing, and extracting information from session logs.

### Context Window Analysis

**File:** [context-analysis.md](context-analysis.md)

Techniques for analyzing context window usage and optimizing session efficiency.

## Related Topics

- [Planning](../planning/) - Sessions often contain plan implementations
- [Commands](../commands/) - Command optimization affects session efficiency
- [Testing](../testing/session-log-fixtures.md) - Creating session log fixtures for tests

---
title: Architecture Documentation
read_when:
  - "understanding erk architecture patterns"
  - "designing interfaces or dependency injection"
  - "working with subprocess execution"
---

# Architecture Documentation

Core architectural patterns and design decisions for the erk codebase.

## Quick Navigation

| When you need to...               | Read this                                        |
| --------------------------------- | ------------------------------------------------ |
| Understand dry-run patterns or DI | [erk-architecture.md](erk-architecture.md)       |
| Choose between Protocol and ABC   | [protocol-vs-abc.md](protocol-vs-abc.md)         |
| Execute shell commands safely     | [subprocess-wrappers.md](subprocess-wrappers.md) |

## Documents in This Category

### Erk Architecture Patterns

**File:** [erk-architecture.md](erk-architecture.md)

Core patterns including dry-run via dependency injection, context regeneration after os.chdir or worktree removal, and the time abstraction layer.

### Protocol vs ABC Design Guide

**File:** [protocol-vs-abc.md](protocol-vs-abc.md)

Decision framework for choosing between Protocol (structural typing) and ABC (nominal typing) when designing interfaces. Includes the @property pattern for frozen dataclasses.

### Subprocess Wrappers

**File:** [subprocess-wrappers.md](subprocess-wrappers.md)

Two-layer pattern for subprocess execution: integration layer (`run_subprocess_with_context`) and CLI layer (`run_with_error_reporting`) wrappers.

## Related Topics

- [CLI Development](../cli/) - Building CLI commands that use these patterns
- [Testing](../testing/) - Testing strategies for architecture patterns

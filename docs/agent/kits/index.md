---
title: Kits Documentation
read_when:
  - "building kit CLI commands"
  - "understanding kit architecture"
  - "creating new kits"
---

# Kits Documentation

Building and understanding the kit system.

## Quick Navigation

| When you need to...                     | Read this                                    |
| --------------------------------------- | -------------------------------------------- |
| Build kit CLI commands                  | [cli-commands.md](cli-commands.md)           |
| Understand kit code architecture        | [code-architecture.md](code-architecture.md) |
| Decide what belongs in kit CLI vs agent | [push-down-pattern.md](push-down-pattern.md) |

## Documents in This Category

### Kit CLI Commands

**File:** [cli-commands.md](cli-commands.md)

Guide to building CLI commands for kits, including the `dot-agent run` interface, command registration, and testing patterns.

### Kit Code Architecture

**File:** [code-architecture.md](code-architecture.md)

Architecture of the kit system: module structure, entry points, and integration with the dot-agent CLI.

### Kit CLI Push Down Pattern

**File:** [push-down-pattern.md](push-down-pattern.md)

When to move mechanical computation from agent prompts to kit CLI commands. Decision framework for LLM vs Python boundaries.

## Related Topics

- [CLI Development](../cli/) - General CLI patterns used by kits
- [Architecture](../architecture/) - Core patterns kits build upon

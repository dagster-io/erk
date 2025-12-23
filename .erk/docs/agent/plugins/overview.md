---
title: Claude Code Plugin System
read_when:
  - understanding plugin architecture
  - installing erk plugins
  - configuring Claude Code plugins
---

# Claude Code Plugin System

> **Note:** This documentation was produced in December 2025 based on Claude Code's plugin system at that time. The plugin system is actively evolving; verify against [official Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for current behavior.

ERK uses Claude Code's native plugin system to distribute commands, agents, skills, and hooks.

## ERK Plugins

| Plugin               | Contents                           | Description                                                          |
| -------------------- | ---------------------------------- | -------------------------------------------------------------------- |
| **erk**              | 8 commands, 1 agent, 1 skill, docs | Workflow commands, git/GitHub integration, Graphite stack management |
| **devrun**           | 1 agent, docs                      | Development tool execution (pytest, pyright, ruff, make, gt)         |
| **dignified-python** | 4 skills, docs                     | Python coding standards with version-aware type annotations          |

## Installation

```bash
# Add ERK marketplace (one time)
/plugin marketplace add dagster-io/erk

# Install plugins
/plugin install erk
/plugin install devrun
/plugin install dignified-python
```

## Architecture

Plugins contain Claude Code artifacts (commands, agents, skills, docs) but NOT scripts.
Scripts remain in the `erk` package and are invoked via `uvx erk@{version} kit exec`.

This provides:

- **Version pinning**: Reproducible behavior across machines
- **No install required**: uvx handles dependency resolution
- **Full erk access**: Scripts use erk_shared, Click decorators, type safety

## Related Documentation

- [Marketplace Configuration](marketplace.md)
- [Plugin Structure](plugin-structure.md)
- [Hook Configuration](hooks.md)
- [uvx Hook Pattern](../architecture/uvx-hooks.md)

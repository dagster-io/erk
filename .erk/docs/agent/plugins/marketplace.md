---
title: Marketplace Configuration
read_when:
  - creating a plugin marketplace
  - configuring marketplace.json
  - publishing erk plugins
---

# Marketplace Configuration

> **Note:** This documentation was produced in December 2025 based on Claude Code's plugin system at that time. The plugin system is actively evolving; verify against [official Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for current behavior.

A marketplace is a git repository containing plugins and a `marketplace.json` registry.

## Directory Structure

```
plugins/
├── .claude-plugin/
│   └── marketplace.json      # Marketplace registry
├── erk/
│   └── .claude-plugin/
│       └── plugin.json       # Plugin metadata
├── devrun/
│   └── ...
└── dignified-python/
    └── ...
```

## marketplace.json Schema

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "erk-plugins",
  "version": "1.0.0",
  "description": "Erk plan-oriented engineering plugins",
  "plugins": [
    {
      "name": "erk",
      "source": "./erk",
      "description": "Erk workflow + git + gt commands"
    },
    {
      "name": "devrun",
      "source": "./devrun",
      "description": "Dev tool execution"
    }
  ]
}
```

### Required Fields

| Field         | Description                         |
| ------------- | ----------------------------------- |
| `name`        | Marketplace identifier (kebab-case) |
| `version`     | Semantic version (x.y.z)            |
| `description` | Human-readable description          |
| `plugins`     | Array of plugin entries             |

### Plugin Entry Fields

| Field         | Description                       |
| ------------- | --------------------------------- |
| `name`        | Plugin identifier (kebab-case)    |
| `source`      | Relative path to plugin directory |
| `description` | What the plugin provides          |

## Adding the Marketplace

Users add the marketplace once:

```bash
/plugin marketplace add dagster-io/erk
```

This registers the marketplace for plugin discovery.

## Updating the Marketplace

```bash
/plugin marketplace update
```

Refreshes the local marketplace cache.

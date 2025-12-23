---
title: Plugin Directory Structure
read_when:
  - creating a new Claude Code plugin
  - configuring plugin.json
  - organizing plugin artifacts
---

# Plugin Directory Structure

> **Note:** This documentation was produced in December 2025 based on Claude Code's plugin system at that time. The plugin system is actively evolving; verify against [official Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for current behavior.

Each plugin follows a standardized layout with automatic component discovery.

## Standard Layout

```
{plugin-name}/
├── .claude-plugin/
│   └── plugin.json           # REQUIRED: Plugin metadata
├── commands/                  # Slash commands
│   └── {command-name}.md
├── agents/                    # Specialized subagents
│   └── {agent-name}.md
├── skills/                    # Auto-activating skills
│   └── {skill-name}/
│       ├── SKILL.md
│       └── references/
├── docs/                      # Documentation
│   └── {doc-name}.md
└── hooks/
    └── hooks.json            # Hook configuration
```

## plugin.json Schema

**Minimal valid plugin.json** (only `name` is required):

```json
{
  "name": "erk"
}
```

**With optional metadata:**

```json
{
  "name": "erk",
  "version": "0.1.0",
  "description": "Erk workflow commands"
}
```

### Required Fields

| Field  | Description                               |
| ------ | ----------------------------------------- |
| `name` | Plugin identifier (kebab-case, lowercase) |

### Optional Fields

| Field         | Description                  |
| ------------- | ---------------------------- |
| `version`     | Semantic version (x.y.z)     |
| `description` | Clear, concise description   |
| `author`      | Object with name, email, url |
| `license`     | SPDX license identifier      |
| `keywords`    | Array of keywords            |
| `repository`  | GitHub URL                   |
| `homepage`    | Documentation URL            |
| `commands`    | Custom path to commands dir  |
| `agents`      | Custom path(s) to agents dir |
| `hooks`       | Custom path to hooks.json    |
| `mcpServers`  | Custom path to .mcp.json     |

## Component Discovery

Claude Code automatically discovers components from standardized directories:

- **commands/**: Files become `/command-name` slash commands
- **agents/**: Files define specialized subagents
- **skills/**: Subdirectories with SKILL.md become loadable skills
- **hooks/**: hooks.json defines lifecycle hooks

## ERK-Specific: No Scripts in Plugins

ERK plugins do NOT contain scripts. Scripts remain in the `erk` package.

Hooks invoke scripts via:

```
uvx erk@{version} kit exec {plugin} {script}
```

See [uvx Hook Pattern](../architecture/uvx-hooks.md) for details.

## Testing During Development

Load a plugin without installation:

```bash
claude --plugin-dir ./plugins/erk
```

---
name: npx-skills
description: This skill should be used when working with the npx skills CLI (skills@1.4.5 by Vercel Labs) for managing agent skills — installing, discovering, updating, and publishing portable AI agent instructions. Use when users mention npx skills commands, skill installation, skills.sh, agentskills.io, skills-lock.json, or the open agent skills ecosystem. Essential for understanding the skills mental model, SKILL.md format, and multi-agent interoperability.
---

# npx skills CLI

## Overview

`npx skills` (npm package `skills@1.4.5`, by Vercel Labs) is the package manager for the open agent skills ecosystem. It manages skill installation, discovery, and updates across 40+ AI coding agents. Skills are portable agent instructions — markdown files that teach agents domain-specific knowledge and workflows.

- **npm package**: `skills@1.4.5` (NOT `skills-cli`)
- **Publisher**: Vercel Labs
- **GitHub**: https://github.com/vercel-labs/skills
- **Registry/discovery**: https://skills.sh/
- **Shared specification**: agentskills.io

## Core Mental Model

### Skills Are Portable Agent Instructions

A **skill** is a directory containing a `SKILL.md` file (and optionally `references/` and `scripts/`). The `SKILL.md` is a markdown document with YAML frontmatter that teaches an agent how to perform a specific task or work with a specific tool.

Skills are agent-agnostic by design. The same skill can be installed for Claude Code, Cursor, Windsurf, Copilot, and 40+ other AI agents. Each agent has its own installation path, but the skill content is shared.

### Project vs Global Scope

- **Project scope** (default): Skills are installed into the project directory (e.g., `.claude/skills/`, `.cursor/skills/`)
- **Global scope** (`-g`): Skills are installed to `~/.skills/` and available across all projects

### Symlink vs Copy

- **Default**: Skills are symlinked from a shared cache, so updates propagate automatically
- **`--copy`**: Creates independent copies that are not affected by updates

### Agent-Specific Directories

Each agent has its own installation path:

| Agent                   | Directory           |
| ----------------------- | ------------------- |
| Claude Code             | `.claude/skills/`   |
| Cursor                  | `.cursor/skills/`   |
| Windsurf                | `.windsurf/skills/` |
| GitHub Copilot          | `.github/skills/`   |
| Multi-agent (canonical) | `.agents/skills/`   |

Use `-a <agent>` to target a specific agent, or `--all` to install for all supported agents.

## SKILL.md Format

### Required Frontmatter

```yaml
---
name: my-skill
description: One-line description of when and how to use this skill
---
```

### Optional Metadata

```yaml
---
name: my-skill
description: When to use this skill
version: 1.0.0
tags: [cli, testing, python]
author: author-name
---
```

### Body Structure

The markdown body after frontmatter contains the agent instructions. Common structure:

1. **Overview** — What the skill covers
2. **When to Use** — Trigger conditions
3. **Core Concepts** — Mental model and key ideas
4. **Command/API Reference** — Detailed usage
5. **Workflow Patterns** — Common multi-step recipes
6. **Resources** — Links to `references/` and `scripts/` subdirectories

### Progressive Disclosure

```
my-skill/
├── SKILL.md            # Primary instructions (always loaded)
├── references/         # Detailed reference docs (loaded on demand)
│   ├── api.md
│   └── config.md
└── scripts/            # Helper scripts
    └── setup.sh
```

## Command Reference

### Discovery

```bash
# Search for skills by keyword
npx skills find [query]
```

Searches the skills.sh registry. Results include skill name, description, source, and security assessment ratings.

### Installation

```bash
# Install a skill (project scope, current agent)
npx skills add <source>

# Install globally
npx skills add <source> -g

# Install for a specific agent
npx skills add <source> -a cursor

# Install for all supported agents
npx skills add <source> --all

# Install as independent copy (not symlinked)
npx skills add <source> --copy

# Install specific subdirectory skill
npx skills add <source> -s <skill-name>

# Skip confirmation prompts
npx skills add <source> -y

# Install with full Git history (for development)
npx skills add <source> --full-depth
```

**Security assessments** are shown during install — ratings from Gen, Socket, and Snyk.

### Inspection

```bash
# List installed skills (project scope)
npx skills list
npx skills ls

# List globally installed skills
npx skills ls -g

# List for a specific agent
npx skills ls -a claude

# Output as JSON
npx skills ls --json
```

### Removal

```bash
# Remove a skill
npx skills remove

# Remove globally
npx skills remove -g

# Remove for a specific agent
npx skills remove -a cursor

# Remove specific subdirectory skill
npx skills remove -s <skill-name>

# Skip confirmation prompts
npx skills remove -y

# Remove from all agents
npx skills remove --all
```

### Updates

```bash
# Check for available updates
npx skills check

# Apply updates
npx skills update
```

### Scaffolding

```bash
# Create a new skill scaffold
npx skills init [name]
```

Creates a new skill directory with a template `SKILL.md` and recommended structure.

### Lock File Operations

```bash
# Restore skills from skills-lock.json
npx skills experimental_install

# Sync skills from node_modules
npx skills experimental_sync
```

`skills-lock.json` tracks `source`, `sourceType`, and `computedHash` per skill for reproducible installations.

## Source Format Reference

Skills can be added from various sources:

| Format                   | Example                                                   |
| ------------------------ | --------------------------------------------------------- |
| GitHub shorthand         | `owner/repo`                                              |
| GitHub with subdirectory | `owner/repo -s skill-name`                                |
| Full GitHub URL          | `https://github.com/owner/repo`                           |
| GitLab URL               | `https://gitlab.com/owner/repo`                           |
| Direct skill path        | `https://github.com/owner/repo/tree/main/skills/my-skill` |
| Local path               | `./path/to/skill`                                         |

## Workflow Patterns

### Install a Skill Globally

```bash
npx skills find "python testing"
npx skills add owner/repo -g -y
npx skills ls -g
```

### Add a Skill to a Project for All Agents

```bash
npx skills add owner/repo --all -y
```

### Create and Publish a Skill

```bash
npx skills init my-new-skill
# Edit my-new-skill/SKILL.md with content
# Push to GitHub
# Register at skills.sh
```

### Update All Skills

```bash
npx skills check
npx skills update
```

### Restore from Lock File

```bash
npx skills experimental_install
```

## Environment Variables

| Variable                    | Purpose                            |
| --------------------------- | ---------------------------------- |
| `INSTALL_INTERNAL_SKILLS=1` | Enable internal skill installation |
| `DISABLE_TELEMETRY`         | Disable usage telemetry            |
| `DO_NOT_TRACK`              | Alternative telemetry opt-out      |

## Version Note

This skill documents `skills@1.4.5` (published 2026-03-13 by Vercel Labs).

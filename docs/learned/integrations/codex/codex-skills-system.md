---
title: Codex Skills System
read_when:
  - "porting erk skills to Codex"
  - "understanding Codex skill discovery and invocation"
  - "creating dual-format skills for Claude and Codex"
  - "comparing Claude and Codex skill architectures"
tripwires:
  - action: "assuming Codex custom prompts are the current approach"
    warning: "Custom prompts (~/.codex/prompts/*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead."
---

# Codex Skills System

How Codex skills work, verified against `codex-rs/core/src/skills/`. Research date: February 2, 2026.

## Skill Directory Structure

Each skill is a directory containing a `SKILL.md` file:

```
.codex/skills/my-skill/
├── SKILL.md              # Required: YAML frontmatter + instructions
├── scripts/              # Optional: executable code
├── references/           # Optional: additional documentation
├── assets/               # Optional: templates, icons
└── agents/
    └── openai.yaml       # Optional: UI metadata, MCP dependencies
```

## SKILL.md Format

YAML frontmatter is required with `name` and `description`:

```yaml
---
name: my-skill-name
description: What this skill does and when to use it
metadata:
  short-description: Brief one-liner
---
# Skill Instructions

Markdown body with detailed instructions for the agent.
Only loaded when the skill is activated (progressive disclosure).
```

### Frontmatter Validation

Source: `codex-rs/core/src/skills/loader.rs`

| Field                        | Required | Max Length | Notes                      |
| ---------------------------- | -------- | ---------- | -------------------------- |
| `name`                       | Yes      | 64 chars   | Skill identifier           |
| `description`                | Yes      | 1024 chars | Used for implicit matching |
| `metadata.short-description` | No       | 1024 chars | Brief description          |

### agents/openai.yaml (Optional)

UI metadata and MCP dependencies:

| Field                  | Type              | Description                                          |
| ---------------------- | ----------------- | ---------------------------------------------------- |
| `display_name`         | string            | Human-readable name                                  |
| `short_description`    | string            | Brief description for UI                             |
| `icon_small`           | path              | Small icon file                                      |
| `icon_large`           | path              | Large icon file                                      |
| `brand_color`          | string            | Brand color for UI                                   |
| `default_prompt`       | string (max 1024) | Default prompt when skill is selected                |
| `dependencies.tools[]` | list              | MCP tool dependencies (type, value, transport, etc.) |

## Discovery Scopes

Skills are loaded from multiple roots in priority order:

| Scope  | Path                                     | Priority |
| ------ | ---------------------------------------- | -------- |
| Repo   | `.codex/skills/` (project-level)         | Highest  |
| User   | `$CODEX_HOME/skills/` (user-installed)   |          |
| System | `$CODEX_HOME/skills/.system/` (embedded) |          |
| Admin  | `/etc/codex/skills/` (on Unix)           | Lowest   |

Deduplication: if a skill name appears in multiple scopes, the highest-priority version wins. Skills are sorted by scope priority, then by name.

Scan limits: max depth 6, max 2000 skill directories per root.

## Invocation

### Explicit

- `$skill-name` mention in the prompt text
- `/skills` command menu in TUI

### Implicit

Codex auto-activates skills when the task description matches the skill's `description` field.

### Progressive Disclosure

At session startup, only `name` and `description` are loaded into context (~50 tokens per skill). The full SKILL.md body is loaded only when the skill is invoked (~2-5K tokens). This is different from Claude, which loads all skill content into context.

## Comparison with Claude Skills

| Aspect               | Claude Code Skills                         | Codex Skills                                         |
| -------------------- | ------------------------------------------ | ---------------------------------------------------- |
| Location             | `.claude/skills/`                          | `.codex/skills/`                                     |
| File format          | `SKILL.md` with optional YAML frontmatter  | `SKILL.md` with required YAML frontmatter            |
| Required frontmatter | None (content-only is valid)               | `name` and `description` required                    |
| Invocation           | `@` references, auto-loaded, hook triggers | `$skill-name` mention, implicit matching             |
| Loading behavior     | All skills loaded into context at startup  | Progressive: metadata at startup, body on invocation |
| Script support       | No (instructions only)                     | Yes (`scripts/` directory for executable code)       |
| UI metadata          | No                                         | Yes (`agents/openai.yaml`)                           |
| Scope levels         | Repo (`.claude/`) or user (`~/.claude/`)   | Repo, user, system, admin (4 levels)                 |
| Commands             | Separate `.claude/commands/` system        | Merged into skills (no separate commands)            |
| Hooks                | PreToolUse, PostToolUse, etc.              | Not available                                        |

## Porting Strategy for Erk

Claude's `.claude/skills/` SKILL.md files are structurally compatible with Codex. Key steps for dual-format support:

1. **Ensure frontmatter compatibility**: Codex requires `name` and `description` in YAML frontmatter. Add these to existing erk skills that lack them.

2. **Install to both directories**: When erk installs skills to a project, write to both `.claude/skills/` and `.codex/skills/`.

3. **Handle commands**: Claude has a separate `.claude/commands/` system. Codex merges commands into skills. Erk commands would need to be represented as Codex skills.

4. **Script support**: Codex skills can include `scripts/` with executable code. This could replace some of erk's hook-based behavior.

5. **No hooks in Codex**: Safety-net hooks (like dignified-python injection on `.py` edits) have no Codex equivalent. Bake critical instructions into the skill body or AGENTS.md.

## Slash Command Translation

Claude uses `/erk:plan-implement` to invoke commands. Codex has no slash commands. Options:

- **$skill-name syntax**: Translate `/erk:plan-implement` to a prompt containing `$erk-plan-implement`. Requires the skill to be installed in `.codex/skills/`.
- **Prompt injection**: Read the skill's SKILL.md content and include it in the prompt text directly. More robust but bypasses Codex's skill discovery.

The reliability of `$skill-name` invocation in `codex exec` mode needs testing before committing to an approach.

## Related Documentation

- [Codex CLI Reference](codex-cli-reference.md) — CLI flags and modes
- [Multi-Agent Portability](multi-agent-portability.md) — Broader multi-agent research

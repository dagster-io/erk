---
title: Codex Skills System
read_when:
  - "porting erk skills to Codex"
  - "implementing dual-target skill installation"
  - "understanding why Codex requires frontmatter that Claude doesn't"
  - "translating Claude slash commands for Codex execution"
tripwires:
  - action: "assuming Codex custom prompts are the current approach"
    warning: "Custom prompts (~/.codex/prompts/*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead."
  - action: "installing skills only to .claude/skills/ when Codex support is needed"
    warning: "Erk has a dual-target architecture. See get_bundled_codex_dir() in artifacts/paths.py and codex_portable_skills() in codex_portable.py for the portability registry."
  - action: "assuming all erk skills are portable to Codex"
    warning: "Only skills in codex_portable_skills() are portable. Skills that depend on Claude-specific features (hooks, session logs, commands) are in claude_only_skills()."
last_audited: "2026-02-08 13:55 PT"
audit_result: clean
---

# Codex Skills System

Research verified against `codex-rs/core/src/skills/` in the [Codex repository](https://github.com/openai/codex). Research date: February 2, 2026.

## Three Design Axes Where Claude and Codex Skills Diverge

Both systems use `SKILL.md` as the entry point, but they diverge on three axes that drive all of erk's dual-target design decisions:

**1. Frontmatter is mandatory in Codex** because Codex uses progressive disclosure — only metadata loads at startup (~50 tokens per skill), with the full body loaded on invocation. Claude loads everything into context at startup, so frontmatter is optional. This means every erk skill needs `name` and `description` frontmatter even though Claude doesn't require it, because omitting frontmatter silently breaks Codex discovery.

**2. Codex has a richer scope model** — four resolution levels (repo, user, system, admin) vs Claude's two (repo, user). Erk only targets repo scope currently, so this doesn't affect installation, but it matters if erk ever ships user-level skills.

**3. Codex supports executable scripts; Claude does not.** Codex skills can include `scripts/`, `references/`, `assets/`, and `agents/openai.yaml`. This means some behaviors erk implements via Claude hooks could theoretically move to Codex scripts — but the two mechanisms are different enough that a shared abstraction isn't practical.

## Codex Skills API Reference

### Skill Directory Structure

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

### SKILL.md Frontmatter

```yaml
---
name: my-skill-name # max 64 chars, required
description: What this skill does and when to use it # max 1024 chars, required
metadata:
  short-description: Brief one-liner # optional
---
```

The markdown body below contains agent instructions, loaded only on invocation.

#### Frontmatter Validation

Source: `codex-rs/core/src/skills/loader.rs`

| Field                        | Required | Max Length | Notes                      |
| ---------------------------- | -------- | ---------- | -------------------------- |
| `name`                       | Yes      | 64 chars   | Skill identifier           |
| `description`                | Yes      | 1024 chars | Used for implicit matching |
| `metadata.short-description` | No       | 1024 chars | Brief description          |

### agents/openai.yaml Field Reference

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

### Discovery Scopes

Skills are loaded from multiple roots in priority order:

| Scope  | Path                                     | Priority |
| ------ | ---------------------------------------- | -------- |
| Repo   | `.codex/skills/` (project-level)         | Highest  |
| User   | `$CODEX_HOME/skills/` (user-installed)   |          |
| System | `$CODEX_HOME/skills/.system/` (embedded) |          |
| Admin  | `/etc/codex/skills/` (on Unix)           | Lowest   |

Deduplication: if a skill name appears in multiple scopes, the highest-priority version wins. Skills are sorted by scope priority, then by name.

Scan limits: max depth 6, max 2000 skill directories per root.

### Invocation

**Explicit:**

- `$skill-name` mention in the prompt text
- `/skills` command menu in TUI

**Implicit:** Codex auto-activates skills when the task description matches the skill's `description` field.

**Progressive Disclosure:** At session startup, only `name` and `description` are loaded into context (~50 tokens per skill). The full SKILL.md body is loaded only when the skill is invoked (~2-5K tokens). This is different from Claude, which loads all skill content into context.

## Claude vs Codex Skills Decision Table

| Aspect               | Claude Code                                  | Codex                                                | Erk Implication                                             |
| -------------------- | -------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------- |
| Location             | `.claude/skills/`                            | `.codex/skills/`                                     | Dual-target install writes to both directories              |
| File format          | `SKILL.md` with optional YAML frontmatter    | `SKILL.md` with required YAML frontmatter            | All erk skills use YAML frontmatter for cross-compatibility |
| Required frontmatter | None (content-only is valid)                 | `name` and `description`                             | All erk skills carry frontmatter to stay Codex-compatible   |
| Loading behavior     | All skills in context at startup             | Progressive: metadata at startup, body on invocation | Codex is more token-efficient for large skill sets          |
| Invocation           | `@` references, auto-loaded, hook triggers   | `$skill-name` mention, implicit matching             | Slash commands need translation (see below)                 |
| Script support       | No                                           | Yes (`scripts/` directory)                           | Could replace some hook-based behavior                      |
| UI metadata          | No                                           | Yes (`agents/openai.yaml`)                           | Not currently used by erk                                   |
| Hooks                | PreToolUse, PostToolUse, etc.                | Not available                                        | Safety-net hooks must be baked into skill body or AGENTS.md |
| Scope levels         | 2 (repo, user)                               | 4 (repo, user, system, admin)                        | Erk only targets repo scope currently                       |
| Commands             | Backwards-compat alias (`.claude/commands/`) | Merged into skills (no separate commands)            | Commands can be ported directly to `.codex/skills/`         |

## Dual-Target Architecture: Why Format Compatibility Enables a Fallback

Erk classifies skills into portable vs Claude-only via a portability registry, then resolves the install source directory based on whether erk is installed as editable or as a wheel.

<!-- Source: src/erk/core/capabilities/codex_portable.py, codex_portable_skills -->

See `codex_portable_skills()` and `claude_only_skills()` in `src/erk/core/capabilities/codex_portable.py` for the canonical portability classification. The deciding factor is whether a skill references Claude-specific features (hooks, session logs, Claude Code commands) — if it does, it's Claude-only.

<!-- Source: src/erk/artifacts/paths.py, get_bundled_codex_dir -->

See `get_bundled_codex_dir()` in `src/erk/artifacts/paths.py` for install-mode-aware path resolution. The key insight: in editable installs, `.codex/` doesn't exist, so the resolver falls back to `.claude/`. This works because Claude's SKILL.md format is a strict subset of Codex's — any SKILL.md with `name` and `description` frontmatter is valid for both systems. The only structural difference is the target install directory (`.claude/skills/` vs `.codex/skills/`), not the file content. Wheel installs bundle Codex skills separately at `erk/data/codex/`.

## Slash Command Translation

Claude uses `/erk:plan-implement` to invoke commands. Codex has no slash command system, creating a translation problem for headless automation.

| Approach         | Mechanism                                      | Trade-off                                                                            |
| ---------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------ |
| `$skill-name`    | Prompt containing `$erk-plan-implement`        | Relies on Codex's description matching; requires skill installed in `.codex/skills/` |
| Prompt injection | Read SKILL.md content and embed in prompt text | More robust but bypasses Codex's progressive disclosure and skill discovery          |

**Open question:** The reliability of `$skill-name` invocation in `codex exec` (headless) mode needs testing. The TUI has a `/skills` menu for explicit invocation, but `codex exec` relies on description matching which may be brittle.

## Anti-Patterns

**WRONG: Assuming hooks can enforce coding standards in Codex.** Claude's PreToolUse hooks (like dignified-python injection on `.py` edits) have no Codex equivalent. For Codex, critical coding standards must live in the skill body or AGENTS.md. There is no lifecycle hook to inject them at the moment of code editing.

**WRONG: Installing all erk skills to `.codex/skills/`.** Skills referencing Claude-specific features (hook configuration, session log analysis, Claude Code commands) will confuse Codex agents with instructions they can't act on. The portability registry exists specifically to prevent this.

## Related Documentation

- [Codex CLI Reference](codex-cli-reference.md) — CLI flags, modes, and permission mapping
- [Multi-Agent Portability](../multi-agent-portability.md) — Broader multi-agent comparison (permission models, session tracking, extensibility)

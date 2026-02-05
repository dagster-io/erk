---
title: Bundled Artifacts (.codex/ Directory)
read_when:
  - understanding what gets bundled with erk releases
  - working with .codex/ directory structure
  - evaluating agent portability
tripwires:
  - action: "adding skills to .codex/ without verifying they work outside Claude Code"
    warning: "Codex portability: Verify skills don't use Claude-only features (hooks, system prompts, TodoWrite). See bundled-artifacts.md for portable vs Claude-only classification."
  - action: "modifying skills in .codex/ that are also in .claude/"
    warning: "TOML duplicate key constraint: A skill can only be defined once. Either in .codex/ (portable) OR .claude/ (Claude-only), never both. See single-canonical-destination pattern in toml-handling.md."
last_audited: "2026-02-05 09:52 PT"
audit_result: edited
---

# Bundled Artifacts (.codex/ Directory)

> **Status**: Speculative architecture. The `.codex/` directory does not exist yet. This doc describes the planned portability strategy for multi-agent support.

## Portability Classification Criteria

When `.codex/` is implemented, skills will be classified as portable or Claude-only:

### Portable Skills

Skills that use only standard features available across agents:

- No hooks (all instructions in SKILL.md)
- No Claude-specific tools (TodoWrite, EnterPlanMode, AskUserQuestion)
- No system prompt overrides
- Work with standard tool set (Read, Write, Edit, Bash, Grep, Glob)

### Claude-Only Skills

Skills that depend on Claude Code exclusive features:

- **Hooks**: PreToolUse/PostToolUse hooks for context injection
- **Extended tools**: Claude-specific tools not in OpenCode/Codex spec

## TOML Duplicate Key Constraint

**Critical rule**: A skill can only exist in ONE location.

TOML doesn't allow duplicate keys. If a skill is defined in both `.codex/` and `.claude/`, config parsing fails:

```toml
# This is invalid TOML
[skills.my-skill]
source = ".codex/skills/my-skill"

[skills.my-skill]  # ERROR: duplicate key
source = ".claude/skills/my-skill"
```

**Pattern**: Single canonical destination:

- **Portable skills** → `.codex/` only (gets copied to agent-specific dir on init)
- **Claude-only skills** → `.claude/` only (never copied)

**Never both.**

## Migration Strategy

When making a skill portable:

1. **Remove Claude-only dependencies** — Remove hook references, replace Claude-specific tools with standard equivalents
2. **Test without hooks** — Verify skill works with hooks disabled
3. **Move to `.codex/`** — `git mv .claude/skills/my-skill .codex/skills/my-skill`
4. **Document portability** — Add `portability: portable` to frontmatter

## Current State

All skills are currently in `.claude/skills/`. See that directory for the current skill inventory. The `.codex/` directory will be created when multi-agent portability work begins.

## Related Documentation

- [multi-agent-portability.md](multi-agent-portability.md) - Agent comparison and session abstraction
- `docs/learned/reference/toml-handling.md` - TOML duplicate key pattern
- `docs/learned/commands/command-portability.md` - Command-level portability patterns

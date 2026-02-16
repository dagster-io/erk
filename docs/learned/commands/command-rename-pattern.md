---
audit_result: clean
last_audited: "2026-02-08 00:00 PT"
read_when:
  - renaming a slash command or skill
  - migrating command invocations across the codebase
  - performing a terminology shift that affects command names
title: Command Rename Pattern
tripwires:
  - action: "renaming any file in .claude/commands/ or .claude/skills/"
    warning: "Read this doc — renames require a full reference sweep, not just a file move"
---

# Command Rename Pattern

Renaming a slash command is a **cross-cutting migration**, not a file operation. The command name appears in invocations, body text, other commands, documentation, hook configurations, AGENTS.md, and the docs index. Missing any location creates silent breakage — stale invocations fail without error, and inconsistent terminology confuses agents.

## Why This Is Hard to Get Right

Slash command names are scattered across many artifact types with no single registry. Unlike code symbols (which produce import errors when renamed), stale command references fail silently — an agent invoking `/erk:old-name` simply gets "command not found" with no pointer to the new name.

The reference locations that are easy to miss:

| Location                                                  | Why It's Missed                                           |
| --------------------------------------------------------- | --------------------------------------------------------- |
| Other command files that invoke or reference this command | Not obvious which commands are related                    |
| `AGENTS.md` skill listing                                 | Updated separately from commands                          |
| Hook configurations in `.claude/hooks/`                   | Hooks reference command names for trigger matching        |
| `docs/learned/` prose mentions                            | Documentation references the old name in explanatory text |
| `docs/learned/**/index.md` auto-generated entries         | Must run `erk docs sync` to regenerate                    |

## Grep Verification Strategy

Three grep passes catch different reference styles:

```bash
# 1. Slash invocations: /namespace:old-name
grep -r "/old-command-name" .

# 2. Prose references (without slash): "the old-name command"
grep -r "old-command-name" docs/ .claude/

# 3. Snake-case variants (implementation may use underscores)
grep -r "old_command_name" .

# 4. Exclude noise
# CHANGELOG mentions are historical — don't update
# .git/ is not your concern
```

After all updates, the final grep for the old name (excluding CHANGELOG and .git/) must return zero results.

## Anti-Pattern: Mechanical Rename Without Terminology Update

**Historical context:** Issue #6410 renamed `/local:todos-clear` to `/local:tasks-clear` but only updated the filename and invocation. The body text still said "todos" everywhere — "Clear all todos", "Todos might become stale". Issue #6412 fixed the terminology throughout.

**The lesson:** When a rename represents a **terminology shift** (not just a naming convention fix), the old term must be replaced everywhere — body text, user-facing messages, variable names, glossary entries, and related documentation. A rename that changes `todos` to `tasks` but leaves "todo list" in the description creates conceptual confusion.

**Decision test:** Is this rename purely mechanical (fixing a typo, applying kebab-case convention) or does it represent a concept change? If the latter, grep for the old _term_ (not just the old command name) and update all occurrences.

## Completion Checklist

- Old command file deleted
- New command file created with updated self-references
- All invocations updated (`/namespace:new-name`)
- Body text terminology updated (if terminology shift)
- Cross-references from other commands updated
- Hook configurations updated if command is hooked
- AGENTS.md skill listing updated
- Zero grep results for old name (excluding CHANGELOG)
- `erk docs sync` run to regenerate index files
- CI passes

## Related Documentation

- [Step Renumbering Checklist](step-renumbering-checklist.md) — similar cross-cutting update pattern for step numbers within commands
- [Optimization Patterns](optimization-patterns.md) — command structure patterns relevant during rename

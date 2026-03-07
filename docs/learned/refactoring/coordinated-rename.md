---
title: Coordinated Cross-Codebase Rename Pattern
read_when:
  - "renaming a command or concept across the codebase"
  - "performing a systematic rename across CLI, TUI, tests, and docs"
  - "coordinating renames that touch 10+ files"
tripwires:
  - action: "renaming a command or concept across the codebase"
    warning: "Follow the 12-point checklist in coordinated-rename.md. Renames typically touch 13-15 files across CLI/TUI/tests/docs/skills. Missing any site causes runtime errors or stale references."
---

# Coordinated Cross-Codebase Rename Pattern

Systematic rename of a command or concept across CLI, TUI, tests, documentation, and skills. Exemplars: cmux `sync` -> `checkout` (13 files), `sync` -> `teleport` (8 files).

## 12-Point Rename Checklist

### Code

1. **Exec script file** — rename the Python file and update the Click command `name=` parameter
2. **Click command name** — the string in `@click.command("name")`
3. **Dataclasses/types** — any frozen dataclasses or type definitions referencing the old name
4. **Exec group registration** — the group's `add_command()` or auto-discovery that picks up the script

### TUI

5. **TUI command registry** — `src/erk/tui/commands/registry.py` maps command names to shell commands
6. **TUI palette actions** — command palette entries that reference the old name
7. **TUI async workers** — background task methods that invoke the command
8. **TUI screens** — any screen displaying or invoking the command by name

### Tests

9. **Unit tests** — test files for the exec script or command
10. **TUI tests** — async test classes that exercise TUI actions invoking the command

### Documentation

11. **docs/learned/ files** — grep for old name across all learned docs
12. **Skills and slash commands** — `.claude/skills/` and `.claude/commands/` referencing the old name

## Execution Strategy

1. **Grep first** — `grep -r "old_name" src/ tests/ docs/ .claude/` to find all occurrences
2. **Rename in dependency order** — start with the source module, then consumers
3. **Preserve serialization names** if they appear in JSON keys, provider names, or YAML values (these may need backward compatibility)
4. **Verify with grep** — after all renames, grep again to confirm zero remaining references to the old name

## Exemplars

- **cmux sync -> checkout:** `src/erk/cli/commands/exec/scripts/cmux_checkout_workspace.py` and 12 consumer files
- **sync -> teleport:** `src/erk/cli/commands/pr/teleport_cmd.py` and 7 consumer files

## Related Topics

- [Systematic Rename Checklist](systematic-rename-checklist.md) — lower-level rename considerations including serialization
- [Post-Refactoring Documentation Audit](post-refactor-documentation-audit.md) — ensuring docs stay current after renames

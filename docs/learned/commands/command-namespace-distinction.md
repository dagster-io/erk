---
title: Command Namespace Distinction
read_when:
  - "invoking commands referenced in objectives or plans"
  - "confused about command namespaces"
  - "command not found errors"
tripwires:
  - action: "invoking a command referenced in objective or plan content"
    warning: "Verify command exists: /local:* and /erk:* are slash commands in .claude/commands/, erk <group> <command> are CLI commands. Do not confuse the two namespaces."
---

# Command Namespace Distinction

## Two Command Types

1. **Slash commands** (`.claude/commands/`)
   - Prefix: `/local:` or `/erk:`
   - Example: `/local:audit-scan`, `/erk:plan-implement`
   - Invocation: Type in Claude Code prompt

2. **CLI commands** (`src/erk/cli/`)
   - Prefix: `erk`
   - Example: `erk docs check`, `erk objective create`
   - Invocation: Run in terminal

## Common Confusion

Objective content may reference `/local:audit-scan` (slash command). Agents have mistakenly tried `erk docs audit-scan` (non-existent CLI command).

## Verification

- Slash commands: Check `.claude/commands/` directory
- CLI commands: Run `erk --help` or `erk <group> --help`

## Related Documentation

- [Commands Index](index.md) — Package overview

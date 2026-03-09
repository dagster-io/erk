---
title: System Folder Convention
read_when:
  - "placing a new command in .claude/commands/"
  - "creating a CI-only or inner skill command"
tripwires:
  - action: "creating a CI-only or workflow-only command outside .claude/commands/erk/system/"
    warning: "CI-only and inner skill commands belong in the system/ subfolder. Read docs/learned/commands/system-folder-convention.md"
---

# System Folder Convention

Commands in `.claude/commands/erk/system/` are not intended for direct user invocation. They are called programmatically by CI workflows, other commands, or CLI code.

## When to Place a Command in `system/`

- The command is invoked by a CI workflow (GitHub Actions)
- The command is an inner skill called by another command
- The command description says "CI-only" or "inner skill"

## Naming

Commands in `system/` automatically get the `/erk:system:` prefix. A file at `.claude/commands/erk/system/foo.md` is invoked as `/erk:system:foo`.

## Discovering System Commands

List current system commands by inspecting the directory:

```bash
ls .claude/commands/erk/system/
```

Each file's frontmatter `description` field documents its purpose.

## User-Facing Commands Stay in `erk/`

Commands that users invoke directly (e.g., `/erk:plan-save`, `/erk:pr-address`) remain in `.claude/commands/erk/`. Only move a command to `system/` when it has no direct user interaction.

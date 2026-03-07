---
title: CLI Command Promotion Pattern
read_when:
  - "promoting a nested CLI command to top-level"
  - "moving a command from a group to the root CLI"
  - "reorganizing CLI command hierarchy"
tripwires:
  - action: "promoting a nested command to top-level"
    warning: "Three files must be updated: cli.py (import + add_command), help_formatter.py (top_level_commands list), and the command module (help text). See command-promotion.md."
---

# CLI Command Promotion Pattern

Pattern for promoting a nested command (under a group like `info`) to a top-level command.

## Steps

### 1. Import in cli.py

<!-- Source: src/erk/cli/cli.py, cli -->

Add the import for the command function at the top of `src/erk/cli/cli.py`, then call `cli.add_command()` near the bottom after the group registrations. See the existing imports and `add_command()` calls in `cli.py` for the pattern.

### 2. Add to help_formatter.py

<!-- Source: src/erk/cli/help_formatter.py, top_level_commands -->

Add the command name to the `top_level_commands` list in `src/erk/cli/help_formatter.py` so it appears in the correct help section. The list is alphabetically ordered.

### 3. Update Command Help Text

Ensure the command's help text makes sense as a top-level command (not referencing its former parent group).

## Exemplar

<!-- Source: src/erk/cli/cli.py, release_notes_cmd -->
<!-- Source: src/erk/cli/help_formatter.py, top_level_commands -->

`release-notes` was promoted from the `info` group to top-level:

- `src/erk/cli/cli.py` — `release_notes_cmd` import and `cli.add_command(release_notes_cmd)` call
- `src/erk/cli/help_formatter.py` — `top_level_commands` list

## Verification

After promotion: `erk release-notes --help` works as a top-level command, and `erk --help` shows it in the top-level commands section.

## Related Topics

- [CLI Development](../cli/) — broader CLI patterns

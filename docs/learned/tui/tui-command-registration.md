---
title: TUI Command Registration
read_when:
  - "adding a new TUI command to the registry"
  - "understanding the 3-place coordination pattern for TUI commands"
  - "working with TUI command categories or display formatters"
tripwires:
  - action: "adding a new TUI command without updating all 3 places"
    warning: "TUI commands require 3-place coordination: registry definition, display formatter, and action inventory. See tui-command-registration.md."
---

# TUI Command Registration

Adding a TUI command requires coordinating three places in the codebase.

## 3-Place Coordination Pattern

When adding a command, update all three:

1. **Display formatter**: A `_display_*()` function that generates the display name
2. **CommandDefinition**: Entry in `get_all_commands()` with id, name, category, availability, and display getter
3. **Action inventory**: Command appears in the correct category

All definitions are in `src/erk/tui/commands/registry.py`.

## Example: `codespace_run_plan`

**Display formatter** (lines 135-137):

<!-- Source: src/erk/tui/commands/registry.py, _display_codespace_run_plan -->

See `_display_codespace_run_plan()` in `src/erk/tui/commands/registry.py` for the display formatter pattern.

**CommandDefinition** (lines 364-371):

<!-- Source: src/erk/tui/commands/registry.py, get_all_commands -->

See `codespace_run_plan` CommandDefinition in `get_all_commands()` in `registry.py`.

## Command Categories

Commands belong to one of three categories (with emoji indicators):

| Category | Emoji | Purpose                |
| -------- | ----- | ---------------------- |
| `ACTION` | `⚡`  | Execute an operation   |
| `OPEN`   | `🔗`  | Open a URL or resource |
| `COPY`   | `📋`  | Copy text to clipboard |

Category emoji mapping is at `registry.py:11-15`.

## Availability Predicates

Commands use `is_available` lambdas to control when they appear. Common predicates include `_is_objectives_view(ctx)` for objective-specific commands.

## Related Topics

- [TUI Documentation](tui.md) - General TUI architecture

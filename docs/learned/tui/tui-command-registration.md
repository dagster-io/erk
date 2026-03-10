---
title: TUI Command Registration
read_when:
  - "adding a new TUI command to the registry"
  - "understanding the 3-place coordination pattern for TUI commands"
  - "working with TUI command categories or display formatters"
tripwires:
  - action: "adding a new TUI command without updating all 3 places"
    warning: "TUI commands require 3-place coordination: registry definition, display formatter, and action inventory. See tui-command-registration.md."
  - action: "adding a CLI flag that affects behavior without checking TUI command palette"
    warning: "TUI command palette generates shell commands via src/erk/tui/commands/registry.py. When adding CLI flags that change behavior, check if TUI-generated commands need the flag too."
curated_in: erk-tui
---

# TUI Command Registration

Adding a TUI command requires coordinating three places in the codebase.

## 3-Place Coordination Pattern

When adding a command, update all three:

1. **Display formatter**: A `_display_*()` function that generates the display name
2. **CommandDefinition**: Entry in `get_all_commands()` with id, name, category, availability, and display getter
3. **Action inventory**: Command appears in the correct category

All definitions are in `src/erk/tui/commands/registry.py`.

## Single Source of Truth: `launch_key` Field

<!-- Source: src/erk/tui/commands/types.py:60 -->

The `CommandDefinition` dataclass has a `launch_key: str | None` field (added in PR #8559) that defines the single-key binding for the Launch modal. Launch keys are assigned directly on each `CommandDefinition` in `get_all_commands()` in `registry.py`.

The `LaunchScreen.__init__()` builds a `_key_to_command_id` dict from these assignments for O(1) key-to-command lookup.

## Current Launch Key Assignments

<!-- Source: src/erk/tui/commands/registry.py -->

### Plan View

| Key | Command             | Description       |
| --- | ------------------- | ----------------- |
| c   | `close_plan`        | Close Plan        |
| d   | `dispatch_to_queue` | Dispatch to Queue |
| l   | `land_pr`           | Land PR           |
| r   | `rebase_remote`     | Rebase Remote     |
| a   | `address_remote`    | Address Remote    |
| w   | `rewrite_remote`    | Rewrite Remote    |
| m   | `cmux_checkout`     | cmux checkout     |

### Objective View

| Key | Command           | Description     |
| --- | ----------------- | --------------- |
| s   | `one_shot_plan`   | Plan (One-Shot) |
| k   | `check_objective` | Check Objective |
| c   | `close_objective` | Close Objective |

**View-mode isolation**: Plan and objective keys are independent namespaces. The key `c` maps to different commands depending on the active view.

**Key change**: Rebase remote changed from `f` to `r` (PR #8560) for mnemonic consistency.

Only ACTION category commands have launch keys. OPEN (browser) and COPY (clipboard) commands have `launch_key=None`.

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
- [TUI Keyboard Shortcuts](keyboard-shortcuts.md) - Complete binding inventory

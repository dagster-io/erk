---
title: TUI Command Registration
read_when:
  - "adding a new TUI command to the registry"
  - "understanding the 3-place coordination pattern for TUI commands"
  - "working with TUI command categories or display formatters"
  - "adding launch keys to TUI commands"
tripwires:
  - action: "adding a new TUI command without updating all 3 places"
    warning: "TUI commands require 3-place coordination: registry definition, display formatter, and action inventory. See tui-command-registration.md."
  - action: "adding a CLI flag that affects behavior without checking TUI command palette"
    warning: "TUI command palette generates shell commands via src/erk/tui/commands/registry.py. When adding CLI flags that change behavior, check if TUI-generated commands need the flag too."
  - action: "adding launch keys to TUI commands outside registry.py"
    warning: "Launch keys are defined in CommandDefinition.launch_key in registry.py. See tui-command-registration.md."
---

# TUI Command Registration

Adding a TUI command requires coordinating three places in the codebase.

## 3-Place Coordination Pattern

When adding a command, update all three:

1. **Display formatter**: A `_display_*()` function that generates the display name
2. **CommandDefinition**: Entry in `get_all_commands()` with id, name, category, availability, and display getter
3. **Action inventory**: Command appears in the correct category

All definitions are in `src/erk/tui/commands/registry.py`.

## Single Source of Truth: CommandDefinition

<!-- Source: src/erk/tui/commands/types.py:36-62 -->

The `CommandDefinition` dataclass (in `types.py:36-62`) defines all command properties:

See `CommandDefinition` in `src/erk/tui/commands/types.py` for the full field list. Key fields include `id`, `name`, `description`, `category`, `shortcut`, `launch_key`, `is_available`, and `get_display_name`. The `launch_key` field (added in PR #8559) assigns a single-key binding for the Launch modal. Only ACTION category commands should have launch keys.

## Launch Key Assignments

<!-- Source: src/erk/tui/commands/registry.py, get_all_commands -->

Launch keys are assigned directly in `CommandDefinition` entries in `get_all_commands()`:

### Plan View Keys

| Command ID          | Launch Key | Line | Action                             |
| ------------------- | ---------- | ---- | ---------------------------------- |
| `close_plan`        | `c`        | 209  | Close the plan                     |
| `dispatch_to_queue` | `d`        | 219  | Dispatch for remote implementation |
| `land_pr`           | `l`        | 229  | Land the PR                        |
| `rebase_remote`     | `r`        | 241  | Rebase remotely                    |
| `address_remote`    | `a`        | 251  | Address review comments remotely   |
| `rewrite_remote`    | `w`        | 261  | Rewrite PR description remotely    |
| `cmux_sync`         | `m`        | 271  | Sync with cmux                     |

### Objective View Keys

| Command ID        | Launch Key | Line | Action                     |
| ----------------- | ---------- | ---- | -------------------------- |
| `one_shot_plan`   | `s`        | 287  | Create one-shot plan       |
| `check_objective` | `k`        | 297  | Check objective validation |
| `close_objective` | `c`        | 307  | Close the objective        |

**View-mode isolation**: Plan and objective keys are independent namespaces. Both use `c` for "close" without conflict because they are mutually exclusive by availability predicates.

**Key change history**: `rebase_remote` was changed from `f` to `r` (PR #8560) for mnemonic consistency.

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
- [TUI Keyboard Shortcuts](keyboard-shortcuts.md) - Complete keyboard binding inventory

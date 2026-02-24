---
title: Adding Commands to TUI
read_when:
  - "adding a new command to the TUI command palette"
  - "implementing TUI actions with streaming output"
  - "understanding the dual-handler pattern for TUI commands"
tripwires:
  - action: "generating TUI commands that depend on optional PlanRowData fields"
    warning: "Implement three-layer validation: registry predicate, handler guard, app-level helper. Never rely on registry predicate alone."
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
---

# Adding Commands to TUI

## Architecture: The Dual-Handler Pattern

Commands follow a **dual-handler pattern**:

1. **Registry** (`src/erk/tui/commands/registry.py`) — Defines `CommandDefinition` with metadata and availability predicates
2. **Handlers** — Implement actual logic in two locations:
   - `ErkDashApp.execute_palette_command()` in `app.py` — Main list context
   - `PlanDetailScreen.execute_command()` — Detail modal context

Commands need different behavior depending on invocation context. See the actual source files for current command definitions and handler implementations.

## Adding a New Command

1. **Add `CommandDefinition`** to `registry.py` with id, name, description, category, shortcut, availability predicate
2. **Add handler** in `ErkDashApp.execute_palette_command()` for main list context
3. **Add handler** in `PlanDetailScreen.execute_command()` for detail modal context
4. **Add registry tests** in `tests/tui/commands/test_registry.py`

## Command Categories

| Category | Emoji     | Use For                                   |
| -------- | --------- | ----------------------------------------- |
| `ACTION` | lightning | Mutative operations (close, submit, land) |
| `OPEN`   | link      | Browser navigation (open issue, PR, run)  |
| `COPY`   | clipboard | Clipboard operations (copy commands)      |

## Three-Layer Null Validation

Commands that depend on optional `PlanRowData` fields require three-layer validation:

### Layer 1: Registry Availability Predicate

Controls whether the command appears in the palette. Necessary but not sufficient.

### Layer 2: Handler Guard Check

The handler must validate again before using optional fields. Handlers can be invoked through keyboard shortcuts or programmatic paths that bypass the palette.

### Layer 3: App-Level Helper (Optional)

For complex commands, extract validation into a helper that encapsulates all guards and fallback chains.

**Why three layers?**

- Registry predicates can become stale if data changes between palette open and execution
- Keyboard shortcuts may bypass the palette entirely
- Python type narrowing doesn't persist across method boundaries

## Remote Workflow Commands

Remote commands dispatch GitHub Actions workflows instead of executing locally. They use streaming subprocess to show dispatch status and workflow URL, but make no local modifications.

| Aspect        | Local Streaming        | Remote Workflow                      |
| ------------- | ---------------------- | ------------------------------------ |
| Execution     | Runs in subprocess     | Triggers GitHub Actions              |
| Duration      | Full command time      | Only dispatch time                   |
| Output        | Command output         | Dispatch confirmation + workflow URL |
| State changes | May modify local files | No local modifications               |

## Key Files

| File                                        | Purpose                                                  |
| ------------------------------------------- | -------------------------------------------------------- |
| `src/erk/tui/commands/registry.py`          | Command definitions and availability predicates          |
| `src/erk/tui/commands/types.py`             | `CommandDefinition`, `CommandContext`, `CommandCategory` |
| `src/erk/tui/app.py`                        | Handler implementations                                  |
| `src/erk/tui/screens/plan_detail_screen.py` | Detail modal handlers                                    |
| `tests/tui/commands/test_registry.py`       | Registry unit tests                                      |

## Related Documentation

- [Command Palette](command-palette.md) — Command palette implementation
- [TUI Architecture](architecture.md) — Overall TUI design

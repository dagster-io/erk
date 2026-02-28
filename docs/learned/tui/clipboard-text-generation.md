---
title: Clipboard Text Generation
read_when:
  - "implementing copy-to-clipboard in the TUI"
  - "adding a new command that supports clipboard copy"
  - "debugging why a copy command returns wrong text"
tripwires:
  - action: "duplicating display name logic for clipboard text"
    warning: "Use get_copy_text() from registry.py as the single source of truth for clipboard text. Display name generators in command definitions are the canonical source. Do not duplicate this logic in app.py or detail screens."
    score: 5
---

# Clipboard Text Generation

The TUI uses a centralized `get_copy_text()` function to generate clipboard text for copy commands. This eliminates duplication between the main plan list and detail screens.

## Single Source of Truth

<!-- Source: src/erk/tui/commands/registry.py:470, get_copy_text -->

`get_copy_text()` in `src/erk/tui/commands/registry.py:470` maps `(command_id, row, view_mode)` to clipboard text:

```python
def get_copy_text(command_id: str, row: PlanRowData, view_mode: ViewMode) -> str | None:
```

It finds the command by ID, checks availability, and delegates to the command's `get_display_name` callback. Returns `None` if the command isn't found, isn't available, or has no display name generator.

## Why Display Name Generators Are Canonical

Each TUI command optionally defines a `get_display_name` callback that generates context-sensitive text. For copy commands, this same text serves as both the display label and the clipboard content:

- `copy_pr_checkout` — generates `gh pr checkout <number>`
- `copy_plan_url` — generates the GitHub URL for the plan

The display name generator is the single place where this text is defined. `get_copy_text()` simply looks up the right generator and calls it.

## Integration with Dual-Handler Pattern

The TUI has two contexts where copy commands execute:

1. **Main plan list** (`app.py`) — handles keyboard shortcuts on the focused row
2. **Detail screen** (`plan_detail_screen.py`) — handles commands for the viewed plan

Both contexts call `get_copy_text()` with the same arguments, ensuring identical clipboard content regardless of where the command is triggered.

## Adding a New Copy Command

1. Define the command in the registry with a `get_display_name` callback
2. Both the main list and detail screen will automatically support it via `get_copy_text()`
3. No additional wiring needed — the function discovers commands from the global registry

## Related Documentation

- [Dual-Handler Pattern](dual-handler-pattern.md) — Main list vs detail screen command handling
- [TUI Command Registration](tui-command-registration.md) — How commands are registered in the registry

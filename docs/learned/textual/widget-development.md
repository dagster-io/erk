---
title: Textual Widget Development Guide
read_when:
  - "creating Textual widgets"
  - "adding ModalScreen dialogs"
  - "implementing keyboard bindings"
  - "writing Textual CSS styles"
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
---

# Textual Widget Development

For standard Textual API patterns (ModalScreen, Bindings, compose(), CSS, widget types), consult the [Textual documentation](https://textual.textualize.io/). This doc focuses on erk-specific patterns.

## Erk TUI Source Layout

| Component | Location                            |
| --------- | ----------------------------------- |
| Main app  | `src/erk/tui/app.py` (`ErkDashApp`) |
| Widgets   | `src/erk/tui/widgets/`              |
| Screens   | `src/erk/tui/screens/`              |
| CSS       | `src/erk/tui/styles/`               |

## Reference Implementations

- **ModalScreens**: `HelpScreen` (`screens/help_screen.py`), `PlanDetailScreen` (`screens/plan_detail_screen.py`), `IssueBodyScreen` (`screens/issue_body_screen.py`)
- **Streaming output**: `CommandOutputPanel` (`widgets/command_output.py`) — uses `RichLog` for live output display
- **Clickable links**: `widgets/clickable_link.py` — demonstrates accessing app properties from widgets

## Related Documentation

- [TUI Architecture](../tui/architecture.md) — Overall TUI design
- [Adding Commands](../tui/adding-commands.md) — Adding TUI commands
- [Command Palette](../tui/command-palette.md) — Command palette implementation

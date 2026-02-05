---
title: Textual CommandPalette Guide
read_when:
  - "implementing command palette in Textual TUI"
  - "hiding system commands from command palette"
  - "get_system_commands method"
  - "removing Keys Quit Screenshot Theme from palette"
  - "adding emoji prefixes to command palette entries"
  - "using CommandCategory for command categorization"
last_audited: "2026-02-05"
audit_result: edited
---

# Textual CommandPalette Guide

For standard Textual CommandPalette patterns (Providers, Hit/DiscoveryHit, Matcher, async generators, Screen.COMMANDS), consult the [Textual documentation](https://textual.textualize.io/). This doc focuses on erk-specific patterns and a critical Textual pitfall.

## System Commands Pitfall

**CRITICAL:** `get_system_commands` must be overridden on the **App class**, not the Screen class. Textual calls `app.get_system_commands(screen)` when opening the palette — it never calls this method on screens.

```python
# WRONG — This method is never called by Textual
class MyModalScreen(ModalScreen):
    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        return iter(())  # Has no effect!

# CORRECT — Override on App class
class MyApp(App):
    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        if isinstance(screen, MyModalScreen):
            return iter(())
        yield from super().get_system_commands(screen)
```

## Erk Command Categories

Erk's TUI command palette uses category-based emoji prefixes to identify command types:

| Category | Emoji     | Use For              | Examples                               |
| -------- | --------- | -------------------- | -------------------------------------- |
| `ACTION` | lightning | Mutative operations  | Close plan, Submit to queue, Land PR   |
| `OPEN`   | link      | Browser navigation   | Open issue, Open PR, Open workflow run |
| `COPY`   | clipboard | Clipboard operations | Copy checkout command                  |

### Dynamic Display Names

Commands can provide context-aware display names through `get_display_name` on `CommandDefinition`. When provided, the palette shows the dynamic name prefixed by the category emoji.

### Text.assemble() for Emoji + Highlighting

When fuzzy search highlighting is present, use `Text.assemble()` to prepend the emoji while preserving Rich text highlighting. See `_format_palette_display()` and `_format_search_display()` in `src/erk/tui/commands/provider.py`.

## Key Files

- `src/erk/tui/commands/types.py` — `CommandCategory` enum, `CommandDefinition` dataclass
- `src/erk/tui/commands/registry.py` — `CATEGORY_EMOJI` mapping, command definitions
- `src/erk/tui/commands/provider.py` — Palette and search display formatting

## Related Documentation

- [Adding Commands](adding-commands.md) — Step-by-step guide for adding TUI commands
- [TUI Architecture](architecture.md) — Overall TUI design

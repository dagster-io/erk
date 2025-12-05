# Documentation Extraction Plan: System Commands in Textual

## Objective

Add documentation for Textual system commands and the `get_system_commands` method to the existing command palette guide.

## Source Information

- **Session ID**: b2420430-1895-4870-9fe6-ce405c4c500c
- **Discovery**: During implementation of hiding system commands from modal command palette

## Documentation Items

### Item 1: Add System Commands Section to command-palette.md

**Type**: Category A (Learning Gap)
**Location**: `docs/agent/tui/command-palette.md`
**Action**: Add new section
**Priority**: High - This knowledge would have saved significant debugging time

**Content to Add** (insert after "Registering Providers at App Level" section, before "Complete Example"):

```markdown
## System Commands

Textual provides built-in system commands that appear in the command palette by default:

- **Keys** - Show help for focused widget and available keys
- **Quit** - Quit the application
- **Screenshot** - Save an SVG screenshot of the current screen
- **Theme** - Change the current theme

### Hiding System Commands

To hide system commands on specific screens, override `get_system_commands` on the **App class** (not the Screen class):

\`\`\`python
from collections.abc import Iterator
from textual.app import App, SystemCommand
from textual.screen import Screen

class MyApp(App):
    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        """Control system command visibility per screen."""
        # Hide system commands on modal screens
        if isinstance(screen, MyModalScreen):
            return iter(())
        # Show default system commands on other screens
        yield from super().get_system_commands(screen)
\`\`\`

**Critical**: The `get_system_commands` method must be on the App class, not the Screen class. Textual calls `app.get_system_commands(screen)` when opening the command palette - it does not call this method on screens.

### Common Mistake

\`\`\`python
# WRONG - This method is never called by Textual
class MyModalScreen(ModalScreen):
    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        return iter(())  # Has no effect!

# CORRECT - Override on App class
class MyApp(App):
    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        if isinstance(screen, MyModalScreen):
            return iter(())
        yield from super().get_system_commands(screen)
\`\`\`

### Import for SystemCommand

When overriding `get_system_commands`, add the import:

\`\`\`python
from textual.app import App, ComposeResult, SystemCommand
\`\`\`
```

### Item 2: Update read_when in command-palette.md frontmatter

**Type**: Category A (Learning Gap)
**Location**: `docs/agent/tui/command-palette.md` frontmatter
**Action**: Update
**Priority**: Medium - Improves discoverability

**Content**:

Add to `read_when` list:
- "hiding system commands from command palette"
- "get_system_commands method"
- "removing Keys Quit Screenshot Theme from palette"
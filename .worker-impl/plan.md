# Extraction Plan: Textual System Commands Override Pattern

## Objective

Document the `get_system_commands` override pattern for hiding Textual built-in commands from specific screens while keeping them available elsewhere.

## Source Information

- **Analyzed Sessions:** f28cdfc9-1dda-4ff5-a0a7-67d786de3b89 (planning), 6ebba3b0-b477-498d-87ed-9c36caf8373e (implementation)
- **Discovery Context:** Implementing command palette for erk dash modal required hiding system commands (Keys, Quit, Screenshot, Theme) from just the modal while keeping them available on the main app screen

## Documentation Items

### Item 1: Add "Hiding System Commands from Specific Screens" to command-palette.md

**Type:** Category B (Teaching - documenting what was built)
**Location:** `docs/agent/tui/command-palette.md`
**Action:** Add new section
**Priority:** Medium (useful for future TUI work)

**Content to add after "Screen-Scoped Commands with COMMANDS" section:**

```markdown
## Hiding System Commands from Specific Screens

Textual includes default system commands (Keys, Quit, Screenshot, Theme) that appear in every command palette. To hide these from specific screens while keeping them available elsewhere, override `get_system_commands`:

```python
from collections.abc import Iterator
from typing import Any
from textual.screen import ModalScreen, Screen

class MyModalScreen(ModalScreen):
    """Modal that hides system commands, showing only custom commands."""
    
    # Register only our custom provider
    COMMANDS = {MyCustomProvider}
    
    def get_system_commands(self, screen: Screen) -> Iterator[Any]:
        """Override to hide default system commands (Keys, Quit, Screenshot, Theme).
        
        This makes the command palette show only our custom commands.
        """
        # Empty generator pattern - return immediately, yield makes it a generator
        return
        yield  # Required to make this a generator function

    # ... rest of screen implementation
```

**Why this pattern:**
- `get_system_commands` normally yields system command tuples
- Returning an empty generator hides all system commands
- The `return; yield` idiom creates an empty generator with correct typing
- Screen-level override only affects that screen; app-level commands remain available elsewhere

**Type annotation note:** Use `Iterator[Any]` as the return type. The actual `SystemCommands` type alias may not be directly importable in all Textual versions.
```

### Item 2: Add empty generator pattern to textual-quirks.md

**Type:** Category A (Learning - API quirk discovered during session)
**Location:** `docs/agent/tui/textual-quirks.md`
**Action:** Add new section under "App Quirks" or create "Generator Quirks" section
**Priority:** Low (edge case but useful when encountered)

**Content:**

```markdown
### Empty Generator Pattern for Override Methods

**Problem**: Some Textual methods like `get_system_commands` return generators. When overriding to return nothing, you need proper generator syntax.

**Wrong approaches:**
```python
# WRONG - returns None, not a generator
def get_system_commands(self, screen: Screen) -> Iterator[Any]:
    return

# WRONG - list is not a generator
def get_system_commands(self, screen: Screen) -> Iterator[Any]:
    return []
```

**Solution**: Use `return; yield` idiom to create an empty generator:

```python
# CORRECT - empty generator
def get_system_commands(self, screen: Screen) -> Iterator[Any]:
    return
    yield  # Makes this a generator function
```

The `yield` statement (even unreachable) tells Python this is a generator function, so `return` returns an empty generator rather than `None`.
```
---
title: Textual CommandPalette Guide
read_when:
  - "implementing command palette in Textual TUI"
  - "creating searchable command menus"
  - "adding keyboard-accessible command discovery"
  - "working with Textual Provider classes"
  - "hiding system commands from command palette"
  - "get_system_commands method"
  - "removing Keys Quit Screenshot Theme from palette"
---

# Textual CommandPalette Guide

This guide covers implementing CommandPalette functionality in Textual applications, including providers, fuzzy search, and screen-scoped commands.

## Overview

The CommandPalette is a searchable command interface (typically activated with Ctrl+P) that lets users discover and execute commands. Key components:

- **CommandPalette widget** - The modal search interface
- **Provider class** - Supplies commands for discovery and search
- **Hit/DiscoveryHit** - Command entries shown to users
- **Matcher** - Fuzzy search and highlighting

## Basic Provider Implementation

Providers are classes that supply commands to the palette. They must implement `discover()` for empty-query results and `search()` for filtered results.

```python
from textual.command import Provider, Hit, DiscoveryHit, Hits

class MyCommandProvider(Provider):
    """Provider for application commands."""

    async def discover(self) -> Hits:
        """Yield commands shown when palette opens (empty query)."""
        yield DiscoveryHit(
            display="Open Settings",
            command=self._open_settings,
            help="Configure application options",
        )
        yield DiscoveryHit(
            display="Show Help",
            command=self._show_help,
            help="Display keyboard shortcuts",
        )

    async def search(self, query: str) -> Hits:
        """Yield scored commands matching the query."""
        matcher = self.matcher(query)

        commands = [
            ("Open Settings", self._open_settings, "Configure application options"),
            ("Show Help", self._show_help, "Display keyboard shortcuts"),
        ]

        for display, callback, help_text in commands:
            match = matcher.match(display)
            if match > 0:
                yield Hit(
                    score=match,
                    match_display=matcher.highlight(display),
                    command=callback,
                    help=help_text,
                )

    def _open_settings(self) -> None:
        """Open the settings screen."""
        self.app.push_screen(SettingsScreen())

    def _show_help(self) -> None:
        """Show help dialog."""
        self.app.push_screen(HelpScreen())
```

## Hit vs DiscoveryHit

Use the right type for the context:

- **DiscoveryHit**: For `discover()` - shown when query is empty, no score needed
- **Hit**: For `search()` - includes match score for ranking results

```python
# DiscoveryHit - no score, uses display directly
yield DiscoveryHit(
    display="My Command",
    command=callback,
    help="Description",
)

# Hit - requires score and highlighted display
yield Hit(
    score=match_score,           # From matcher.match()
    match_display=highlighted,   # From matcher.highlight()
    command=callback,
    help="Description",
)
```

## Fuzzy Search with Matcher

The `matcher()` method provides fuzzy search capabilities:

```python
async def search(self, query: str) -> Hits:
    matcher = self.matcher(query)

    for name, callback in self._commands:
        # match() returns score (0 = no match, higher = better)
        score = matcher.match(name)
        if score > 0:
            yield Hit(
                score=score,
                match_display=matcher.highlight(name),  # Highlights matched chars
                command=callback,
            )
```

Key matcher methods:

- `matcher.match(text)` - Returns match score (0 if no match)
- `matcher.highlight(text)` - Returns Text with matched characters highlighted

## Screen-Scoped Commands with COMMANDS

Register providers at the Screen level for context-specific commands that only appear when that screen is active:

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.command import Provider, Hits, DiscoveryHit

class DashboardCommands(Provider):
    """Commands only available on DashboardScreen."""

    @property
    def dashboard(self) -> "DashboardScreen":
        """Type-safe access to current screen."""
        assert isinstance(self.screen, DashboardScreen)
        return self.screen

    async def discover(self) -> Hits:
        yield DiscoveryHit(
            display="Refresh Dashboard",
            command=self.dashboard.action_refresh,
        )
        yield DiscoveryHit(
            display="Toggle Filter Panel",
            command=self.dashboard.action_toggle_filters,
        )

    async def search(self, query: str) -> Hits:
        # ... fuzzy search implementation
        pass


class DashboardScreen(Screen):
    """Dashboard with screen-specific commands."""

    # Register the provider - only active when this screen is displayed
    COMMANDS = {DashboardCommands}

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def action_refresh(self) -> None:
        self.query_one(DataTable).refresh()

    def action_toggle_filters(self) -> None:
        # Toggle filter visibility
        pass
```

## Provider Context Properties

Providers have access to runtime context via these properties:

```python
class MyProvider(Provider):
    async def discover(self) -> Hits:
        # Access the application instance
        app = self.app

        # Access currently active screen
        screen = self.screen

        # Access currently focused widget
        focused = self.focused

        # Use context for dynamic commands
        if isinstance(self.screen, EditorScreen):
            yield DiscoveryHit(
                display="Save File",
                command=self.screen.action_save,
            )
```

**Late binding best practice**: Capture context at execution time, not at discovery time:

```python
# GOOD - context captured when command executes
async def discover(self) -> Hits:
    yield DiscoveryHit(
        display="Focus Editor",
        command=self._focus_editor,  # Method captures self.screen at call time
    )

def _focus_editor(self) -> None:
    # self.screen is current when this runs
    editor = self.screen.query_one(TextArea)
    editor.focus()

# BAD - captures screen at discovery time (may be stale)
async def discover(self) -> Hits:
    screen = self.screen  # Captured too early!
    yield DiscoveryHit(
        display="Focus Editor",
        command=lambda: screen.query_one(TextArea).focus(),
    )
```

## Async Generator Pattern

Provider methods use async generators (not returning lists):

```python
from textual.command import Hits  # Type alias for AsyncIterator[Hit | DiscoveryHit]

async def discover(self) -> Hits:
    """Async generator - yields results one by one."""
    # Yield each command individually
    yield DiscoveryHit(display="Command 1", command=self._cmd1)
    yield DiscoveryHit(display="Command 2", command=self._cmd2)

    # Can include conditional logic
    if self.app.dark:
        yield DiscoveryHit(display="Light Mode", command=self._light_mode)
    else:
        yield DiscoveryHit(display="Dark Mode", command=self._dark_mode)

async def search(self, query: str) -> Hits:
    """Can do async operations between yields."""
    matcher = self.matcher(query)

    for cmd in await self._fetch_commands():  # Async data fetch
        score = matcher.match(cmd.name)
        if score > 0:
            yield Hit(score=score, match_display=matcher.highlight(cmd.name), command=cmd.run)
```

Benefits of async generators:

- **Lazy evaluation** - Results computed on demand
- **Early termination** - Can stop after enough results found
- **Memory efficient** - No large list allocations
- **Async support** - Can await between yields

## Closure Pattern for Parameterized Commands

Use `functools.partial` for commands that need parameters:

```python
from functools import partial

class ProjectCommands(Provider):
    async def discover(self) -> Hits:
        # Get projects from app state
        projects = self.app.project_list

        for project in projects:
            yield DiscoveryHit(
                display=f"Open: {project.name}",
                command=partial(self._open_project, project.id),
                help=f"Open project {project.name}",
            )

    def _open_project(self, project_id: str) -> None:
        """Open a specific project."""
        self.app.open_project(project_id)
```

**Why `partial()` over lambda:**

```python
# GOOD - partial is picklable and debuggable
command=partial(self._open, project_id)

# AVOID - lambdas can have closure issues, harder to debug
command=lambda: self._open(project_id)  # project_id may not be captured correctly in loops
```

## Registering Providers at App Level

For global commands available on all screens, register at the App level:

```python
from textual.app import App

class MyApp(App):
    """Application with global command palette."""

    # Global providers available everywhere
    COMMANDS = App.COMMANDS | {GlobalCommands, ThemeCommands}

    # Enable command palette with Ctrl+P (default)
    BINDINGS = [
        ("ctrl+p", "command_palette", "Commands"),
    ]
```

## System Commands

Textual provides built-in system commands that appear in the command palette by default:

- **Keys** - Show help for focused widget and available keys
- **Quit** - Quit the application
- **Screenshot** - Save an SVG screenshot of the current screen
- **Theme** - Change the current theme

### Hiding System Commands

To hide system commands on specific screens, override `get_system_commands` on the **App class** (not the Screen class):

```python
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
```

**Critical**: The `get_system_commands` method must be on the App class, not the Screen class. Textual calls `app.get_system_commands(screen)` when opening the command palette - it does not call this method on screens.

### Common Mistake

```python
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
```

### Import for SystemCommand

When overriding `get_system_commands`, add the import:

```python
from textual.app import App, ComposeResult, SystemCommand
```

## Complete Example

```python
from functools import partial
from textual.app import App, ComposeResult
from textual.command import Provider, Hit, DiscoveryHit, Hits
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable


class IssueCommands(Provider):
    """Commands for working with issues."""

    @property
    def issue_screen(self) -> "IssueScreen":
        assert isinstance(self.screen, IssueScreen)
        return self.screen

    async def discover(self) -> Hits:
        yield DiscoveryHit(
            display="Refresh Issues",
            command=self.issue_screen.action_refresh,
            help="Reload issue list from server",
        )

        # Dynamic commands based on selection
        if selected := self.issue_screen.selected_issue:
            yield DiscoveryHit(
                display=f"Open #{selected.number}",
                command=partial(self._open_issue, selected.number),
            )

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        commands = [
            ("Refresh Issues", self.issue_screen.action_refresh, "Reload issue list"),
            ("Create Issue", self.issue_screen.action_create, "Create new issue"),
            ("Close Issue", self.issue_screen.action_close, "Close selected issue"),
        ]

        for display, callback, help_text in commands:
            score = matcher.match(display)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(display),
                    command=callback,
                    help=help_text,
                )

    def _open_issue(self, number: int) -> None:
        self.app.push_screen(IssueDetailScreen(number))


class IssueScreen(Screen):
    """Screen displaying issue list."""

    COMMANDS = {IssueCommands}

    @property
    def selected_issue(self) -> Issue | None:
        # Return currently selected issue
        pass

    def action_refresh(self) -> None:
        pass

    def action_create(self) -> None:
        pass

    def action_close(self) -> None:
        pass


class MyApp(App):
    COMMANDS = App.COMMANDS | {GlobalCommands}

    def on_mount(self) -> None:
        self.push_screen(IssueScreen())
```

## Key Takeaways

1. **Use DiscoveryHit for discover(), Hit for search()** - They have different required fields
2. **Screen.COMMANDS for context-specific commands** - Provider only active on that screen
3. **Use self.matcher() for fuzzy search** - Handles scoring and highlighting
4. **Capture context late** - Access self.screen/self.app in methods, not closures
5. **Use functools.partial for parameters** - More reliable than lambdas
6. **Async generators yield results** - Don't return lists

"""Modal screen for quick-launch of ACTION commands."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label

from erk.tui.commands.registry import CATEGORY_EMOJI, get_available_commands
from erk.tui.commands.types import CommandCategory, CommandContext, CommandDefinition

# Single-key mappings for ACTION commands, grouped by view context.
# Plan keys and objective keys can reuse letters because get_available_commands
# already filters by view mode—plan commands only appear in Plans/Learn views,
# objective commands only in Objectives view.
LAUNCH_KEYS: dict[str, str] = {
    # Plan actions
    "close_plan": "c",
    "submit_to_queue": "s",
    "land_pr": "l",
    "fix_conflicts_remote": "f",
    "address_remote": "a",
    # Objective actions
    "close_objective": "c",
    "one_shot_plan": "s",
    "check_objective": "k",
}


class LaunchScreen(ModalScreen[str | None]):
    """Compact modal for two-keystroke ACTION command execution.

    Shows only ACTION-category commands available for the current row,
    each mapped to a single key press.
    """

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Close"),
        Binding("q", "dismiss_cancel", "Close"),
    ]

    DEFAULT_CSS = """
    LaunchScreen {
        align: center middle;
    }

    #launch-dialog {
        width: 72;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #launch-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
    }

    .launch-row {
        margin-left: 2;
    }

    #launch-footer {
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, *, ctx: CommandContext) -> None:
        """Initialize with the command context for the selected row.

        Builds the key-to-command mapping eagerly so it is available for
        testing without requiring a Textual app context.

        Args:
            ctx: Command context containing row data and view mode
        """
        super().__init__()
        self._ctx = ctx

        # Build key-to-command mapping and ordered rows for rendering
        available = get_available_commands(ctx)
        action_commands = [cmd for cmd in available if cmd.category == CommandCategory.ACTION]

        self._key_to_command_id: dict[str, str] = {}
        self._launch_rows: list[tuple[str, CommandDefinition]] = []
        for cmd in action_commands:
            key = LAUNCH_KEYS.get(cmd.id)
            if key is not None:
                self._key_to_command_id[key] = cmd.id
                self._launch_rows.append((key, cmd))

    def compose(self) -> ComposeResult:
        """Build the launch menu from precomputed ACTION command rows."""
        emoji = CATEGORY_EMOJI[CommandCategory.ACTION]

        with Vertical(id="launch-dialog"):
            yield Label("Launch", id="launch-title")

            if self._launch_rows:
                for key, cmd in self._launch_rows:
                    display_name = cmd.name
                    if cmd.get_display_name is not None:
                        display_name = cmd.get_display_name(self._ctx)
                    yield Label(
                        f"  \\[{key}]  {emoji} {cmd.description}: {display_name}",
                        classes="launch-row",
                    )
            else:
                yield Label("  No actions available", classes="launch-row")

            yield Label("Press a key or Esc to cancel", id="launch-footer")

    def on_key(self, event: Key) -> None:
        """Handle key press—dispatch to command if mapped."""
        command_id = self._key_to_command_id.get(event.key)
        if command_id is not None:
            event.prevent_default()
            self.dismiss(command_id)

    def action_dismiss_cancel(self) -> None:
        """Dismiss the screen with no action."""
        self.dismiss(None)

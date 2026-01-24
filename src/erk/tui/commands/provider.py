"""Command provider for Textual command palette."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from rich.text import Text
from textual.command import DiscoveryHit, Hit, Hits, Provider

from erk.tui.commands.registry import CATEGORY_EMOJI, get_available_commands, get_display_name
from erk.tui.commands.types import CommandContext

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp, PlanDetailScreen


def _format_highlighted_display(emoji: str, highlighted: object) -> str | Text:
    """Format highlighted command name with emoji prefix.

    Args:
        emoji: Category emoji to prepend
        highlighted: Highlighted name (Content, str, or Rich Text)

    Returns:
        Formatted display string or Text object
    """
    if isinstance(highlighted, Text):
        return Text.assemble(f"{emoji} ", highlighted)
    return f"{emoji} {highlighted}"


class MainListCommandProvider(Provider):
    """Command provider for main plan list view.

    Provides commands for the currently selected plan row directly from main list.
    """

    @property
    def _app(self) -> ErkDashApp:
        """Get the ErkDashApp instance.

        Returns:
            The ErkDashApp instance

        Raises:
            AssertionError: If app is not ErkDashApp
        """
        from erk.tui.app import ErkDashApp

        app = self.app
        if not isinstance(app, ErkDashApp):
            msg = f"MainListCommandProvider expected ErkDashApp, got {type(app)}"
            raise AssertionError(msg)
        return app

    def _get_context(self) -> CommandContext | None:
        """Build command context from selected row.

        Returns:
            CommandContext if a row is selected, None otherwise
        """
        row = self._app._get_selected_row()
        if row is None:
            return None
        return CommandContext(row=row)

    async def discover(self) -> Hits:
        """Show available commands when palette opens.

        Yields:
            DiscoveryHit for each available command
        """
        ctx = self._get_context()
        if ctx is None:
            return

        for cmd in get_available_commands(ctx):
            emoji = CATEGORY_EMOJI[cmd.category]
            name = get_display_name(cmd, ctx)
            yield DiscoveryHit(
                f"{emoji} {name}",
                partial(self._app.execute_palette_command, cmd.id),
            )

    async def search(self, query: str) -> Hits:
        """Fuzzy search commands.

        Args:
            query: The search query from user input

        Yields:
            Hit for each matching command, with fuzzy match score
        """
        ctx = self._get_context()
        if ctx is None:
            return

        matcher = self.matcher(query)

        for cmd in get_available_commands(ctx):
            name = get_display_name(cmd, ctx)
            score = matcher.match(name)
            if score > 0:
                emoji = CATEGORY_EMOJI[cmd.category]
                highlighted = matcher.highlight(name)
                display = _format_highlighted_display(emoji, highlighted)
                yield Hit(
                    score,
                    display,
                    partial(self._app.execute_palette_command, cmd.id),
                )


class PlanCommandProvider(Provider):
    """Command provider for plan detail modal.

    Provides commands specific to the selected plan via Textual's command palette.
    """

    @property
    def _detail_screen(self) -> PlanDetailScreen:
        """Get the PlanDetailScreen from current screen context.

        Returns:
            The PlanDetailScreen instance

        Raises:
            AssertionError: If not called from a PlanDetailScreen
        """
        from erk.tui.app import PlanDetailScreen

        screen = self.screen
        if not isinstance(screen, PlanDetailScreen):
            msg = f"PlanCommandProvider expected PlanDetailScreen, got {type(screen)}"
            raise AssertionError(msg)
        return screen

    def _get_context(self) -> CommandContext:
        """Build command context from current screen state.

        Returns:
            CommandContext with the selected plan's row data
        """
        return CommandContext(row=self._detail_screen._row)

    async def discover(self) -> Hits:
        """Show available commands when palette opens.

        Yields:
            DiscoveryHit for each available command
        """
        ctx = self._get_context()
        for cmd in get_available_commands(ctx):
            emoji = CATEGORY_EMOJI[cmd.category]
            name = get_display_name(cmd, ctx)
            yield DiscoveryHit(
                f"{emoji} {name}",
                partial(self._detail_screen.execute_command, cmd.id),
            )

    async def search(self, query: str) -> Hits:
        """Fuzzy search commands.

        Args:
            query: The search query from user input

        Yields:
            Hit for each matching command, with fuzzy match score
        """
        matcher = self.matcher(query)
        ctx = self._get_context()

        for cmd in get_available_commands(ctx):
            name = get_display_name(cmd, ctx)
            score = matcher.match(name)
            if score > 0:
                emoji = CATEGORY_EMOJI[cmd.category]
                highlighted = matcher.highlight(name)
                display = _format_highlighted_display(emoji, highlighted)
                yield Hit(
                    score,
                    display,
                    partial(self._detail_screen.execute_command, cmd.id),
                )

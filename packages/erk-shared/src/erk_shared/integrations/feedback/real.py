"""Real implementations of UserFeedback."""

import click

from erk_shared.integrations.feedback.abc import UserFeedback
from erk_shared.output.output import user_output


class InteractiveFeedback(UserFeedback):
    """Feedback shown in interactive mode (all messages)."""

    def info(self, message: str) -> None:
        """Show informational message."""
        user_output(message)

    def success(self, message: str) -> None:
        """Show success message in green."""
        user_output(click.style(message, fg="green"))

    def error(self, message: str) -> None:
        """Show error message in red."""
        user_output(click.style(message, fg="red"))


class SuppressedFeedback(UserFeedback):
    """Feedback suppressed in script mode (only errors shown).

    Used when --script flag is active to keep output clean for
    shell integration handler to parse activation script path.
    """

    def info(self, message: str) -> None:
        """Suppress informational message in script mode."""
        pass

    def success(self, message: str) -> None:
        """Suppress success message in script mode."""
        pass

    def error(self, message: str) -> None:
        """Show error message even in script mode."""
        user_output(click.style(message, fg="red"))

"""Output utilities for CLI commands with clear intent."""

import sys
from typing import Any

import click


def user_output(
    message: Any | None = None,
    nl: bool = True,
    color: bool | None = None,
) -> None:
    """Output informational message for human users.

    Routes to stderr so shell integration can capture structured data
    on stdout while users still see progress/status messages.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        nl: Print a newline after the message. Enabled by default.
        color: Force showing or hiding colors and other styles. By default, Click
            will remove color if the output does not look like an interactive terminal.
    """
    click.echo(message, nl=nl, err=True, color=color)


def machine_output(
    message: Any | None = None,
    nl: bool = True,
    color: bool | None = None,
) -> None:
    """Output structured data for machine/script consumption.

    Routes to stdout for shell wrappers to capture. Should only be used
    for final output like activation script paths.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        nl: Print a newline after the message. Enabled by default.
        color: Force showing or hiding colors and other styles. By default, Click
            will remove color if the output does not look like an interactive terminal.
    """
    click.echo(message, nl=nl, err=False, color=color)


def user_confirm(prompt: str) -> bool:
    """Prompt user for confirmation with proper stderr flushing.

    Always flush stderr before prompting to ensure any preceding
    user_output() messages are visible.

    Args:
        prompt: The confirmation prompt to display.

    Returns:
        True if the user confirmed, False otherwise.
    """
    sys.stderr.flush()
    return click.confirm(prompt, default=False, err=True)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 34s" or "45s")

    Example:
        >>> format_duration(154.5)
        '2m 34s'
        >>> format_duration(45.2)
        '45s'
    """
    if seconds < 60:
        return f"{seconds:.0f}s"

    minutes = int(seconds / 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"

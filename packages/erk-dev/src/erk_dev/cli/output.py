"""Output utilities for CLI commands with clear intent."""

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

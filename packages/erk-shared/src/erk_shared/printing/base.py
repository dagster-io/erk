"""Base class for printing wrapper operations.

This module provides a base class that contains common functionality for
printing wrapper implementations, eliminating code duplication across
PrintingGit, PrintingLocalGitHub, and PrintingGraphite.
"""

from typing import Any

import click

from erk_shared.output.output import machine_output, user_output


class PrintingBase:
    """Base class for printing wrapper implementations.

    Provides common printing infrastructure for delegating operations
    while optionally printing styled output for executed commands.

    This base class contains the common initialization and printing methods
    that are identical across all Printing wrapper implementations.
    """

    def __init__(self, wrapped: Any, *, script_mode: bool = False, dry_run: bool = False) -> None:
        """Create a printing wrapper around an Ops implementation.

        Args:
            wrapped: The Ops implementation to wrap
            script_mode: True when running in --script mode (output to stderr)
            dry_run: True when running in --dry-run mode (adds indicator to output)
        """
        self._wrapped = wrapped
        self._script_mode = script_mode
        self._dry_run = dry_run

    def _emit(self, message: str) -> None:
        """Emit message based on script mode."""
        if self._script_mode:
            user_output(message)
        else:
            # In non-script mode, use machine_output for stdout
            machine_output(message)

    def _format_command(self, cmd: str) -> str:
        """Format a command for display with optional dry-run indicator."""
        styled_cmd = click.style(f"  {cmd}", dim=True)
        if self._dry_run:
            dry_run_marker = click.style(" (dry run)", fg="bright_black")
            checkmark = click.style(" ✓", fg="green")
            return styled_cmd + dry_run_marker + checkmark
        else:
            checkmark = click.style(" ✓", fg="green")
            return styled_cmd + checkmark

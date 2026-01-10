"""List available capabilities."""

import click

from erk.core.capabilities.registry import list_capabilities
from erk_shared.output.output import user_output


@click.command("list")
def list_cmd() -> None:
    """List available capabilities.

    Shows all registered capabilities with their descriptions.
    This command does not require being in a git repository.
    """
    caps = list_capabilities()

    if not caps:
        user_output("No capabilities registered.")
        return

    user_output("Available capabilities:")
    for cap in caps:
        user_output(f"  {cap.name:25} {cap.description}")

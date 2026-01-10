"""List available capabilities."""

import click

from erk.core.capabilities.registry import list_capabilities
from erk_shared.output.output import user_output


@click.command("list")
def list_cmd() -> None:
    """List available capabilities.

    Shows all registered capabilities with their descriptions and scope.
    This command does not require being in a git repository.
    """
    caps = list_capabilities()

    if not caps:
        user_output("No capabilities registered.")
        return

    user_output("Available capabilities:")
    for cap in caps:
        scope_label = f"[{cap.scope}]"
        user_output(f"  {cap.name:25} {scope_label:10} {cap.description}")

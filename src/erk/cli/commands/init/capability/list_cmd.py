"""List available capabilities."""

import click

from erk.core.capabilities import list_capabilities
from erk.core.capabilities.groups import list_groups
from erk_shared.output.output import user_output


@click.command("list")
def list_cmd() -> None:
    """List available capabilities and groups.

    Shows all registered capabilities and groups with their descriptions.
    Groups expand to their member capabilities when installed.
    This command does not require being in a git repository.
    """
    caps = list_capabilities()
    groups = list_groups()

    if not caps and not groups:
        user_output("No capabilities registered.")
        return

    if caps:
        user_output("Available capabilities:")
        for cap in caps:
            user_output(f"  {cap.name:25} {cap.description}")

    if groups:
        user_output("\nAvailable groups:")
        for group in groups:
            members = ", ".join(group.members)
            user_output(f"  {group.name:25} {group.description}")
            user_output(f"    → {members}")

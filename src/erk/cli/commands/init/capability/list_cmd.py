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

    # Group by scope
    project_caps = [c for c in caps if c.scope == "project"]
    user_caps = [c for c in caps if c.scope == "user"]

    # Sort each group alphabetically by name
    project_caps.sort(key=lambda c: c.name)
    user_caps.sort(key=lambda c: c.name)

    # Output project capabilities
    if project_caps:
        user_output(click.style("Project capabilities:", bold=True))
        for cap in project_caps:
            styled_name = click.style(f"{cap.name:25}", fg="cyan")
            user_output(f"  {styled_name} {cap.description}")

    # Output user capabilities with blank line separator
    if user_caps:
        if project_caps:
            user_output("")  # Blank line between sections
        user_output(click.style("User capabilities:", bold=True))
        for cap in user_caps:
            styled_name = click.style(f"{cap.name:25}", fg="cyan")
            user_output(f"  {styled_name} {cap.description}")

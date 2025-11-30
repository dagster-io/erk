"""List registered planner boxes."""

import click
from rich.console import Console
from rich.table import Table

from erk.core.context import ErkContext


@click.command("list")
@click.pass_obj
def list_planners(ctx: ErkContext) -> None:
    """List all registered planner boxes."""
    planners = ctx.planner_registry.list_planners()
    default_name = ctx.planner_registry.get_default_name()

    if not planners:
        click.echo("No planners registered.", err=True)
        click.echo("\nUse 'erk planner register <name>' to register a codespace.", err=True)
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("name", style="cyan", no_wrap=True)
    table.add_column("repository", style="yellow", no_wrap=True)
    table.add_column("configured", no_wrap=True)
    table.add_column("last connected", no_wrap=True)

    for planner in sorted(planners, key=lambda p: p.name):
        # Name with default indicator
        name_cell = planner.name
        if planner.name == default_name:
            name_cell = f"[cyan bold]{planner.name}[/cyan bold] (default)"
        else:
            name_cell = f"[cyan]{planner.name}[/cyan]"

        # Configured status
        configured_cell = "[green]yes[/green]" if planner.configured else "[yellow]no[/yellow]"

        # Last connected
        if planner.last_connected_at:
            # Format as relative time or date
            last_connected = planner.last_connected_at.strftime("%Y-%m-%d %H:%M")
        else:
            last_connected = "-"

        table.add_row(name_cell, planner.repository, configured_cell, last_connected)

    # Output table to stderr (consistent with erk conventions)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)

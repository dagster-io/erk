"""List registered codespaces."""

import click
from rich.console import Console
from rich.table import Table

from erk.core.context import ErkContext


@click.command("list")
@click.pass_obj
def list_codespaces(ctx: ErkContext) -> None:
    """List all registered codespaces."""
    codespaces = ctx.codespace_registry.list_codespaces()
    default_name = ctx.codespace_registry.get_default_name()

    if not codespaces:
        click.echo("No codespaces registered.", err=True)
        click.echo("\nUse 'erk codespace setup <name>' to create a codespace.", err=True)
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("name", style="cyan", no_wrap=True)
    table.add_column("gh_name", style="yellow", no_wrap=True)
    table.add_column("created", no_wrap=True)

    for codespace in sorted(codespaces, key=lambda c: c.name):
        # Name with default indicator
        if codespace.name == default_name:
            name_cell = f"[cyan bold]{codespace.name}[/cyan bold] (default)"
        else:
            name_cell = f"[cyan]{codespace.name}[/cyan]"

        # Format created date
        created_cell = codespace.created_at.strftime("%Y-%m-%d %H:%M")

        table.add_row(name_cell, codespace.gh_name, created_cell)

    # Output table to stderr (consistent with erk conventions)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)

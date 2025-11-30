"""Unregister a planner box."""

import click

from erk.core.context import ErkContext


@click.command("unregister")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def unregister_planner(ctx: ErkContext, name: str, force: bool) -> None:
    """Remove a planner box from the registry.

    This does not delete the codespace - it only removes the registration.
    """
    planner = ctx.planner_registry.get(name)
    if planner is None:
        click.echo(f"Error: No planner named '{name}' found.", err=True)
        click.echo("\nUse 'erk planner list' to see registered planners.", err=True)
        raise SystemExit(1)

    # Check if this is the default
    is_default = ctx.planner_registry.get_default_name() == name

    if not force:
        msg = f"Unregister planner '{name}'?"
        if is_default:
            msg = f"Unregister planner '{name}' (currently the default)?"
        if not click.confirm(msg):
            click.echo("Cancelled.", err=True)
            raise SystemExit(0)

    ctx.planner_registry.unregister(name)

    click.echo(f"Unregistered planner '{name}'.", err=True)
    if is_default:
        click.echo("Note: Default planner has been cleared.", err=True)

    # Suggest setting a new default if there are other planners
    remaining = ctx.planner_registry.list_planners()
    if remaining and is_default:
        click.echo("\nUse 'erk planner set-default <name>' to set a new default.", err=True)

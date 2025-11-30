"""Set the default planner box."""

import click

from erk.core.context import ErkContext


@click.command("set-default")
@click.argument("name")
@click.pass_obj
def set_default_planner(ctx: ErkContext, name: str) -> None:
    """Set the default planner box.

    The default planner is used when running 'erk planner' without arguments.
    """
    planner = ctx.planner_registry.get(name)
    if planner is None:
        click.echo(f"Error: No planner named '{name}' found.", err=True)
        click.echo("\nUse 'erk planner list' to see registered planners.", err=True)
        raise SystemExit(1)

    ctx.planner_registry.set_default(name)
    click.echo(f"Set '{name}' as the default planner.", err=True)

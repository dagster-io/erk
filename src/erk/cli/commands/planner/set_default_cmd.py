"""Set the default planner box."""

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("set-default")
@click.argument("name")
@click.pass_obj
def set_default_planner(ctx: ErkContext, name: str) -> None:
    """Set the default planner box.

    The default planner is used when running 'erk planner' without arguments.
    """
    _planner = Ensure.not_none(
        ctx.planner_registry.get(name),
        f"No planner named '{name}' found.\n\nUse 'erk planner list' to see registered planners.",
    )

    ctx.planner_registry.set_default(name)
    click.echo(f"Set '{name}' as the default planner.", err=True)

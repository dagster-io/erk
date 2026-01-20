"""Set the default codespace."""

import click

from erk.cli.ensure import Ensure
from erk.core.codespace.registry_real import set_default_codespace
from erk.core.context import ErkContext


@click.command("set-default")
@click.argument("name")
@click.pass_obj
def set_default_codespace_cmd(ctx: ErkContext, name: str) -> None:
    """Set the default codespace.

    The default codespace is used when running 'erk codespace' without arguments.
    """
    _codespace = Ensure.not_none(
        ctx.codespace_registry.get(name),
        f"No codespace named '{name}' found.\n\n"
        "Use 'erk codespace list' to see registered codespaces.",
    )

    config_path = ctx.erk_installation.get_codespaces_config_path()
    set_default_codespace(config_path, name)
    click.echo(f"Set '{name}' as the default codespace.", err=True)

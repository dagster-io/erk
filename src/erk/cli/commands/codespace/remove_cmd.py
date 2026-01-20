"""Remove a registered codespace."""

import click

from erk.core.codespace.registry_real import unregister_codespace
from erk.core.context import ErkContext


@click.command("remove")
@click.argument("name")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def remove_codespace(ctx: ErkContext, name: str, *, force: bool) -> None:
    """Remove a codespace from the registry.

    This does not delete the codespace - it only removes the registration.
    """
    codespace = ctx.codespace_registry.get(name)
    if codespace is None:
        click.echo(f"Error: No codespace named '{name}' found.", err=True)
        click.echo("\nUse 'erk codespace list' to see registered codespaces.", err=True)
        raise SystemExit(1)

    # Check if this is the default
    is_default = ctx.codespace_registry.get_default_name() == name

    if not force:
        msg = f"Remove codespace '{name}'?"
        if is_default:
            msg = f"Remove codespace '{name}' (currently the default)?"
        if not click.confirm(msg):
            click.echo("Cancelled.", err=True)
            raise SystemExit(0)

    config_path = ctx.erk_installation.get_codespaces_config_path()
    unregister_codespace(config_path, name)

    click.echo(f"Removed codespace '{name}'.", err=True)
    if is_default:
        click.echo("Note: Default codespace has been cleared.", err=True)

    # Suggest setting a new default if there are other codespaces
    remaining = ctx.codespace_registry.list_codespaces()
    # Filter out the one we just removed (registry may still have it in memory)
    remaining = [c for c in remaining if c.name != name]
    if remaining and is_default:
        click.echo("\nUse 'erk codespace set-default <name>' to set a new default.", err=True)

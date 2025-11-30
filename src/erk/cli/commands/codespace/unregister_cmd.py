"""Remove a codespace from the local registry."""

import click
from erk_shared.output.output import user_output

from erk.core.context import ErkContext


@click.command("unregister")
@click.argument("friendly_name")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@click.pass_obj
def unregister_codespace(ctx: ErkContext, friendly_name: str, yes: bool) -> None:
    """Remove a codespace from the local registry.

    This only removes the codespace from erk's local tracking.
    It does NOT delete the codespace from GitHub.

    Examples:

        erk codespace unregister old-space

        # Skip confirmation
        erk codespace unregister old-space --yes
    """
    registry = ctx.codespace_registry

    # Check codespace exists in registry
    codespace = registry.get(friendly_name)
    if codespace is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Codespace '{friendly_name}' not found in registry.\n\n"
            + "List registered codespaces with:\n"
            + "  erk codespace list"
        )
        raise SystemExit(1)

    # Confirm unless --yes
    if not yes:
        user_output(f"This will unregister '{friendly_name}' from erk.")
        user_output(f"  GitHub name: {codespace.gh_name}")
        user_output(f"  Repository: {codespace.repository}")
        user_output("")
        user_output("The codespace will NOT be deleted from GitHub.")
        user_output("")

        if not click.confirm("Continue?"):
            user_output("Cancelled.")
            raise SystemExit(0)

    registry.unregister(friendly_name)

    user_output(click.style("", fg="green") + f"Unregistered '{friendly_name}'")
    user_output("")
    user_output("To delete the codespace from GitHub:")
    user_output(f"  gh codespace delete -c {codespace.gh_name}")

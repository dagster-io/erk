"""Connect to a registered codespace via SSH."""

import click
from erk_shared.output.output import user_output

from erk.core.context import ErkContext


@click.command("connect")
@click.argument("friendly_name")
@click.pass_obj
def connect_codespace(ctx: ErkContext, friendly_name: str) -> None:
    """SSH into a registered codespace.

    This command connects to a codespace that has been registered
    with 'erk codespace register'. It uses the friendly name
    instead of GitHub's opaque codespace name.

    Examples:

        erk codespace connect my-planning-space

        erk codespace connect erk-dev
    """
    registry = ctx.codespace_registry
    github = ctx.codespace_github

    # Get codespace from registry
    codespace = registry.get(friendly_name)
    if codespace is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Codespace '{friendly_name}' not found in registry.\n\n"
            + "List registered codespaces with:\n"
            + "  erk codespace list\n\n"
            + "Register an existing codespace with:\n"
            + "  erk codespace register <friendly-name>"
        )
        raise SystemExit(1)

    # Check if codespace still exists on GitHub
    gh_info = github.get_codespace(codespace.gh_name)
    if gh_info is None:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Codespace '{friendly_name}' no longer exists on GitHub.\n\n"
            + "The codespace may have been deleted.\n\n"
            + "Options:\n"
            + f"  Remove from registry: erk codespace unregister {friendly_name}\n"
            + "  Create a new codespace: erk codespace create <name>"
        )
        raise SystemExit(1)

    # Check state
    if gh_info.state == "Shutdown":
        user_output(f"Codespace '{friendly_name}' is shutdown. Starting...")
        user_output("(This may take a moment)")
        user_output("")

    # Update last_connected timestamp before connecting
    registry.update_last_connected(friendly_name, ctx.time.now())

    user_output(f"Connecting to '{friendly_name}'...")

    # SSH - replaces process, never returns
    github.ssh_replace(codespace.gh_name)

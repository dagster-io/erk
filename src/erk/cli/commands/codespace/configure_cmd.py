"""Interactive configuration wizard for codespaces."""

import click
from erk_shared.output.output import user_output

from erk.core.context import ErkContext


@click.command("configure")
@click.argument("friendly_name")
@click.pass_obj
def configure_codespace(ctx: ErkContext, friendly_name: str) -> None:
    """Interactive wizard to configure a codespace for development.

    This command connects to the codespace via SSH and guides you
    through the setup steps needed for development:

    \b
    1. Run: claude login (authenticate Claude Code)
    2. Run: gh auth login (if needed)
    3. Run: uv sync (install dependencies)
    4. Type 'exit' when done

    After exiting SSH, you'll be prompted to mark the codespace
    as configured.

    Examples:

        erk codespace configure my-planning-space
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

    # Check if already configured
    if codespace.configured:
        user_output(f"Codespace '{friendly_name}' is already marked as configured.")
        user_output("")
        if not click.confirm("Run configuration wizard again?"):
            user_output("Cancelled.")
            raise SystemExit(0)

    # Check if codespace exists on GitHub
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

    # Display instructions
    user_output(f"Configuring codespace: {friendly_name}")
    user_output("")
    user_output("This will open an SSH session. Complete these steps:")
    user_output("  1. Run: claude login")
    user_output("  2. Run: gh auth login (if needed)")
    user_output("  3. Run: uv sync (if Python project)")
    user_output("  4. Type 'exit' when done")
    user_output("")
    user_output(click.style("", dim=True) + "Press Enter to connect...")

    try:
        click.getchar()
    except (KeyboardInterrupt, EOFError):
        user_output("\nCancelled.")
        raise SystemExit(1) from None

    user_output("")
    user_output("Connecting to codespace...")
    user_output(click.style("" * 60, dim=True))
    user_output("")

    # SSH - using interactive mode (subprocess.run) so we can continue after
    exit_code = github.ssh_interactive(codespace.gh_name)

    user_output("")
    user_output(click.style("" * 60, dim=True))
    user_output("")

    if exit_code != 0:
        user_output(
            click.style("Warning: ", fg="yellow") + f"SSH session exited with code {exit_code}"
        )
        user_output("")

    # Prompt to mark as configured
    user_output("Configuration steps completed?")
    user_output("")

    if click.confirm("Mark codespace as configured?", default=True):
        registry.mark_configured(friendly_name)
        registry.update_last_connected(friendly_name, ctx.time.now())

        user_output("")
        user_output(
            click.style("", fg="green") + f"Codespace '{friendly_name}' marked as configured."
        )
        user_output("")
        user_output("To connect later:")
        user_output(f"  erk codespace connect {friendly_name}")
    else:
        user_output("")
        user_output("Configuration not marked as complete.")
        user_output("Run this command again when ready:")
        user_output(f"  erk codespace configure {friendly_name}")

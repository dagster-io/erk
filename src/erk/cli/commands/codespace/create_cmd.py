"""Create a new GitHub codespace and register it."""

import click
from erk_shared.output.output import user_output

from erk.core.codespace.types import RegisteredCodespace
from erk.core.context import ErkContext


@click.command("create")
@click.argument("friendly_name")
@click.option(
    "--repo",
    required=True,
    help="Repository in owner/repo format (e.g., 'schrockn/erk').",
)
@click.option(
    "--branch",
    default="main",
    help="Branch to create codespace from (default: main).",
)
@click.option(
    "--machine",
    default="standardLinux32gb",
    help="Machine type (default: standardLinux32gb).",
)
@click.option(
    "--notes",
    help="Optional notes about this codespace.",
)
@click.pass_obj
def create_codespace(
    ctx: ErkContext,
    friendly_name: str,
    repo: str,
    branch: str,
    machine: str,
    notes: str | None,
) -> None:
    """Create a new GitHub codespace and register it with a friendly name.

    This creates a new codespace on GitHub and automatically registers
    it in erk's local registry with the given friendly name.

    Examples:

        erk codespace create my-dev-space --repo schrockn/erk

        erk codespace create feature-work --repo schrockn/erk --branch feature-x

        erk codespace create big-space --repo schrockn/erk --machine standardLinux64gb
    """
    registry = ctx.codespace_registry
    github = ctx.codespace_github

    # Check friendly_name not already registered
    existing = registry.get(friendly_name)
    if existing is not None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Name '{friendly_name}' is already registered.\n\n"
            + "Choose a different name or unregister the existing one:\n"
            + f"  erk codespace unregister {friendly_name}"
        )
        raise SystemExit(1)

    # Create codespace on GitHub
    user_output(f"Creating codespace for {repo} on branch {branch}...")
    user_output(f"  Machine type: {machine}")
    user_output("")

    try:
        gh_info = github.create_codespace(repo, branch, machine)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to create codespace: {e}")
        raise SystemExit(1) from None

    user_output(click.style("✓", fg="green") + f" Codespace created: {gh_info.name}")
    user_output("")

    # Wait for codespace to be available
    if gh_info.state != "Available":
        user_output("Waiting for codespace to become available...")
        available = github.wait_for_available(gh_info.name)
        if not available:
            user_output(
                click.style("Warning: ", fg="yellow")
                + "Codespace may not be fully available yet.\n"
                + "You can check status with: erk codespace list"
            )

    # Register in local registry
    codespace = RegisteredCodespace(
        friendly_name=friendly_name,
        gh_name=gh_info.name,
        repository=gh_info.repository,
        branch=gh_info.branch,
        machine_type=gh_info.machine_type,
        configured=False,
        registered_at=ctx.time.now(),
        last_connected_at=None,
        notes=notes,
    )

    registry.register(codespace)

    user_output(click.style("✓", fg="green") + f" Registered as '{friendly_name}'")
    user_output("")
    user_output("Next step: Configure the codespace for development:")
    user_output(f"  erk codespace configure {friendly_name}")

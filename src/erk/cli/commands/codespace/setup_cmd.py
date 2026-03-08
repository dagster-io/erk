"""Set up a new codespace for remote Claude execution."""

import click

from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.real import register_codespace, set_default_codespace

DEFAULT_MACHINE_TYPE = "premiumLinux"


@click.command("setup")
@click.argument("name", required=False)
@click.option(
    "-r",
    "--repo",
    default=None,
    help="Repository to create codespace from (owner/repo). Defaults to current repo.",
)
@click.option(
    "-b",
    "--branch",
    default=None,
    help="Branch to create codespace from. Defaults to default branch.",
)
@click.option(
    "-m",
    "--machine",
    default=DEFAULT_MACHINE_TYPE,
    help=f"Machine type for the codespace (default: {DEFAULT_MACHINE_TYPE}).",
)
@click.pass_obj
def setup_codespace(
    ctx: ErkContext,
    *,
    name: str | None,
    repo: str | None,
    branch: str | None,
    machine: str,
) -> None:
    """Create and register a new codespace for remote Claude execution.

    Creates a GitHub Codespace via the REST API, registers it in the local
    registry, and opens an SSH connection for Claude login.

    If NAME is not provided, generates one from the repository name.

    After setup, run 'erk codespace' to connect and launch Claude.
    """
    # Generate name from repo if not provided
    if name is None:
        # Try to derive from current repo or use a default
        if ctx.repo_info is not None:
            name = f"{ctx.repo_info.name}-codespace"
        else:
            name = "erk-codespace"
        click.echo(f"Using codespace name: {name}", err=True)

    # Check if name already exists
    existing = ctx.codespace_registry.get(name)
    if existing is not None:
        click.echo(f"Error: A codespace named '{name}' already exists.", err=True)
        click.echo("\nUse 'erk codespace [name]' to connect to it.", err=True)
        raise SystemExit(1)

    owner, repo_name = resolve_owner_repo(ctx, target_repo=repo)
    owner_repo = f"{owner}/{repo_name}"

    # Get repository ID for REST API call
    click.echo(f"Creating codespace '{name}'...", err=True)
    try:
        repo_id = ctx.codespace.get_repo_id(owner_repo)
    except RuntimeError as e:
        click.echo(f"Failed to get repository ID for '{owner_repo}': {e}", err=True)
        raise SystemExit(1) from e

    # Create the codespace via gateway
    try:
        gh_name = ctx.codespace.create_codespace(
            repo_id=repo_id,
            machine=machine,
            display_name=name,
            branch=branch,
        )
    except RuntimeError as e:
        click.echo(f"Codespace creation failed: {e}", err=True)
        raise SystemExit(1) from e

    registered = RegisteredCodespace(
        name=name,
        gh_name=gh_name,
        created_at=ctx.time.now(),
    )
    config_path = ctx.erk_installation.get_codespaces_config_path()
    new_registry = register_codespace(config_path, registered)

    # Set as default if first codespace
    if len(new_registry.list_codespaces()) == 1:
        set_default_codespace(config_path, name)
        click.echo(f"Registered codespace '{name}' (set as default)", err=True)
    else:
        click.echo(f"Registered codespace '{name}'", err=True)

    # Open SSH connection for Claude login
    click.echo("", err=True)
    click.echo("Opening SSH connection for Claude login...", err=True)
    click.echo("", err=True)

    login_result = ctx.codespace.run_ssh_command(gh_name, "claude login")

    if login_result != 0:
        click.echo("", err=True)
        click.echo("Note: Claude login may have failed or was cancelled.", err=True)
        retry_cmd = f"gh codespace ssh -c {gh_name} -- -t 'claude login'"
        click.echo(f"You can retry with: {retry_cmd}", err=True)

    click.echo("", err=True)
    click.echo("Setup complete! Use 'erk codespace' to connect.", err=True)

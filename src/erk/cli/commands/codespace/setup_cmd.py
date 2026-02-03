"""Set up a new codespace for remote Claude execution."""

import json
import subprocess

import click

from erk.cli.subprocess_utils import run_with_error_reporting
from erk.core.context import ErkContext
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.real import register_codespace, set_default_codespace

DEFAULT_MACHINE_TYPE = "premiumLinux"


def _get_repo_id(*, repo: str | None, ctx: ErkContext) -> int:
    """Get the GitHub repository database ID.

    Uses the --repo flag if provided, otherwise derives from ctx.repo_info.
    """
    if repo is not None:
        owner_repo = repo
    elif ctx.repo_info is not None:
        owner_repo = f"{ctx.repo_info.owner}/{ctx.repo_info.name}"
    else:
        click.echo("Error: No repository specified and no repo info available.", err=True)
        click.echo("Use --repo owner/repo to specify the repository.", err=True)
        raise SystemExit(1)

    result = run_with_error_reporting(
        ["gh", "api", f"repos/{owner_repo}", "--jq", ".id"],
        error_prefix=f"Failed to get repository ID for '{owner_repo}'",
        troubleshooting=["Ensure gh is authenticated", "Check the repository exists"],
    )
    return int(result.stdout.strip())


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

    # Get repository ID for REST API call
    click.echo(f"Creating codespace '{name}'...", err=True)
    repo_id = _get_repo_id(repo=repo, ctx=ctx)

    # Build gh api REST call to create codespace directly
    # This bypasses the broken machines endpoint that gh codespace create uses
    # GH-API-AUDIT: REST - POST user/codespaces
    cmd = [
        "gh",
        "api",
        "--method",
        "POST",
        "/user/codespaces",
        "-f",
        f"repository_id={repo_id}",
        "-f",
        f"machine={machine}",
        "-f",
        f"display_name={name}",
        "-f",
        "devcontainer_path=.devcontainer/devcontainer.json",
    ]

    if branch is not None:
        cmd.extend(["-f", f"ref={branch}"])

    click.echo(f"Running: {' '.join(cmd)}", err=True)
    click.echo("", err=True)

    result = run_with_error_reporting(
        cmd,
        error_prefix="Codespace creation failed",
        troubleshooting=[
            "Ensure gh is authenticated with codespace permissions",
            "Check that the machine type is valid",
        ],
    )

    # Parse the JSON response to get the codespace name
    response = json.loads(result.stdout)
    gh_name = response["name"]

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

    # GH-API-AUDIT: REST - codespace SSH connection
    login_result = subprocess.run(
        [
            "gh",
            "codespace",
            "ssh",
            "-c",
            gh_name,
            "--",
            "-t",
            "claude login",
        ],
        check=False,
    )

    if login_result.returncode != 0:
        click.echo("", err=True)
        click.echo("Note: Claude login may have failed or was cancelled.", err=True)
        retry_cmd = f"gh codespace ssh -c {gh_name} -- -t 'claude login'"
        click.echo(f"You can retry with: {retry_cmd}", err=True)

    click.echo("", err=True)
    click.echo("Setup complete! Use 'erk codespace' to connect.", err=True)

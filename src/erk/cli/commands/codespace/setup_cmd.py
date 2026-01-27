"""Set up a new codespace for remote Claude execution."""

import json
import subprocess

import click

from erk.core.context import ErkContext
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.real import register_codespace, set_default_codespace


def _find_codespace_by_display_name(display_name: str) -> dict | None:
    """Find a codespace by its display name."""
    # GH-API-AUDIT: REST - GET user/codespaces
    result = subprocess.run(
        ["gh", "codespace", "list", "--json", "name,repository,displayName"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    content = result.stdout.strip()
    if not content:
        return None

    try:
        codespaces = json.loads(content)
        for cs in codespaces:
            if cs.get("displayName") == display_name:
                return cs
        return None
    except json.JSONDecodeError:
        return None


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
@click.pass_obj
def setup_codespace(
    ctx: ErkContext,
    *,
    name: str | None,
    repo: str | None,
    branch: str | None,
) -> None:
    """Create and register a new codespace for remote Claude execution.

    Creates a GitHub Codespace, registers it in the local registry, and
    opens an SSH connection for Claude login.

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

    # Build gh codespace create command
    # GH-API-AUDIT: REST - POST user/codespaces
    cmd = ["gh", "codespace", "create"]

    if repo:
        cmd.extend(["--repo", repo])

    if branch:
        cmd.extend(["--branch", branch])

    cmd.extend(["--display-name", name])

    click.echo(f"Creating codespace '{name}'...", err=True)
    click.echo(f"Running: {' '.join(cmd)}", err=True)
    click.echo("", err=True)

    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        click.echo(f"\nCodespace creation failed (exit code {result.returncode}).", err=True)
        raise SystemExit(1)

    # Find and register the created codespace
    click.echo("", err=True)
    click.echo("Looking up created codespace...", err=True)

    codespace = _find_codespace_by_display_name(name)
    if codespace is None:
        click.echo(f"Warning: Could not find codespace '{name}' to register.", err=True)
        raise SystemExit(1)

    gh_name = codespace.get("name", "")

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

"""Create a new planner codespace."""

import json
import subprocess

import click

from erk.core.context import ErkContext
from erk.core.planner.types import RegisteredPlanner


def _find_codespace_by_display_name(display_name: str) -> dict | None:
    """Find a codespace by its display name."""
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


@click.command("create")
@click.argument("name", default="erk-planner-node")
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
    "--run/--dry-run",
    default=False,
    help="Actually run the command (default: just print it).",
)
@click.pass_obj
def create_planner(
    ctx: ErkContext,
    name: str,
    repo: str | None,
    branch: str | None,
    run: bool,
) -> None:
    """Create a new GitHub Codespace for use as a planner.

    Creates a codespace with the right devcontainer configuration and
    automatically registers it as a planner.

    The codespace will be created with:
    - GitHub CLI pre-installed
    - Claude Code pre-installed
    - uv and project dependencies

    After creation, run 'erk planner configure NAME' to set up authentication.
    """
    # Check if name already exists
    existing = ctx.planner_registry.get(name)
    if existing is not None:
        click.echo(f"Error: A planner named '{name}' already exists.", err=True)
        raise SystemExit(1)

    # Build the gh command
    cmd = ["gh", "codespace", "create"]

    if repo:
        cmd.extend(["--repo", repo])

    if branch:
        cmd.extend(["--branch", branch])

    cmd.extend(["--display-name", name])
    cmd.extend(["--devcontainer-path", ".devcontainer/devcontainer.json"])

    if run:
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
            click.echo(f"Run 'erk planner register {name}' manually.", err=True)
            raise SystemExit(1)

        gh_name = codespace.get("name", "")
        repository = codespace.get("repository", "")

        planner = RegisteredPlanner(
            name=name,
            gh_name=gh_name,
            repository=repository,
            configured=False,
            registered_at=ctx.time.now(),
            last_connected_at=None,
        )
        ctx.planner_registry.register(planner)

        # Set as default if first planner
        if len(ctx.planner_registry.list_planners()) == 1:
            ctx.planner_registry.set_default(name)
            click.echo(f"Registered planner '{name}' (set as default)", err=True)
        else:
            click.echo(f"Registered planner '{name}'", err=True)

        click.echo("", err=True)
        click.echo("Next step:", err=True)
        click.echo(f"  erk planner configure {name}", err=True)
    else:
        click.echo("Run this command to create the codespace:", err=True)
        click.echo("", err=True)
        click.echo(f"  {' '.join(cmd)}", err=True)
        click.echo("", err=True)
        click.echo("Or run with --run to execute directly:", err=True)
        click.echo(f"  erk planner create {name} --run", err=True)
        click.echo("", err=True)
        click.echo("After creation, configure authentication:", err=True)
        click.echo(f"  erk planner configure {name}", err=True)

"""Register an existing GitHub Codespace as a planner box."""

import json
import subprocess

import click

from erk.core.context import ErkContext
from erk.core.planner.types import RegisteredPlanner


def _list_codespaces() -> list[dict]:
    """List available codespaces from GitHub.

    Returns:
        List of codespace dicts with name, repository, displayName fields
    """
    result = subprocess.run(
        ["gh", "codespace", "list", "--json", "name,repository,displayName"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    # JSON parsing requires exception handling for malformed data
    content = result.stdout.strip()
    if not content:
        return []
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        return []
    except json.JSONDecodeError:
        return []


@click.command("register")
@click.argument("name")
@click.pass_obj
def register_planner(ctx: ErkContext, name: str) -> None:
    """Register an existing GitHub Codespace as a planner box.

    Lists available codespaces and prompts you to select one.
    The selected codespace will be registered under NAME.
    """
    # Check if name already exists
    existing = ctx.planner_registry.get(name)
    if existing is not None:
        click.echo(f"Error: A planner named '{name}' already exists.", err=True)
        click.echo(f"Use 'erk planner unregister {name}' first to remove it.", err=True)
        raise SystemExit(1)

    # List available codespaces
    click.echo("Fetching available codespaces...", err=True)
    codespaces = _list_codespaces()

    if not codespaces:
        click.echo("No codespaces found.", err=True)
        click.echo("\nCreate a codespace first, then run this command again.", err=True)
        raise SystemExit(1)

    # Display available codespaces
    click.echo("\nAvailable codespaces:", err=True)
    for i, cs in enumerate(codespaces, 1):
        display_name = cs.get("displayName", cs.get("name", "unknown"))
        repo = cs.get("repository", "unknown")
        click.echo(f"  {i}. {display_name} ({repo})", err=True)

    # Prompt for selection
    click.echo("", err=True)
    selection = click.prompt(
        "Select codespace number",
        type=click.IntRange(1, len(codespaces)),
    )

    selected = codespaces[selection - 1]
    gh_name = selected.get("name", "")
    repository = selected.get("repository", "")

    if not gh_name:
        click.echo("Error: Could not get codespace name.", err=True)
        raise SystemExit(1)

    # Create and register the planner
    planner = RegisteredPlanner(
        name=name,
        gh_name=gh_name,
        repository=repository,
        configured=False,
        registered_at=ctx.time.now(),
        last_connected_at=None,
    )

    ctx.planner_registry.register(planner)

    # If this is the first planner, set it as default
    if len(ctx.planner_registry.list_planners()) == 1:
        ctx.planner_registry.set_default(name)
        click.echo(f"\nRegistered planner '{name}' (set as default)", err=True)
    else:
        click.echo(f"\nRegistered planner '{name}'", err=True)

    click.echo(f"\nRun 'erk planner configure {name}' for initial setup.", err=True)

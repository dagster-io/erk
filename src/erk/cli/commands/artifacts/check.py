"""Artifact check command."""

from pathlib import Path

import click

from erk.artifacts.staleness import check_staleness, get_current_version, is_dev_mode
from erk.artifacts.state import load_artifact_state


@click.command()
def check() -> None:
    """Check artifact sync status."""
    project_dir = Path.cwd()

    click.echo(f"erk version: {get_current_version()}")
    click.echo(f"Dev mode: {is_dev_mode(project_dir)}")

    state = load_artifact_state(project_dir)
    if state:
        click.echo(f"Installed version: {state.version}")
    else:
        click.echo("Installed version: (not initialized)")

    result = check_staleness(project_dir)

    if result.is_stale:
        click.echo(click.style(f"Status: {result.reason}", fg="yellow"))
    else:
        click.echo(click.style("Status: up to date", fg="green"))

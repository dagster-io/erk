"""Artifact check command."""

import click

from erk.artifacts.staleness import check_staleness, get_current_version
from erk.artifacts.state import load_artifact_state
from erk.core.context import ErkContext
from erk.core.repo_discovery import in_erk_repo


@click.command()
@click.pass_obj
def check(ctx: ErkContext) -> None:
    """Check artifact sync status."""
    project_dir = ctx.cwd

    click.echo(f"erk version: {get_current_version()}")
    click.echo(f"In erk repo: {in_erk_repo(project_dir)}")

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

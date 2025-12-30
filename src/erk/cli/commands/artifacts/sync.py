"""Artifact sync command."""

from pathlib import Path

import click

from erk.artifacts.staleness import check_staleness, is_dev_mode
from erk.artifacts.sync import sync_artifacts


@click.command()
@click.option("--force", is_flag=True, help="Sync even if up to date")
def sync(force: bool) -> None:
    """Sync erk artifacts to project."""
    project_dir = Path.cwd()

    if is_dev_mode(project_dir):
        click.echo("Dev mode - artifacts read from source, nothing to sync")
        return

    if not force:
        result = check_staleness(project_dir)
        if not result.is_stale:
            click.echo("Artifacts are up to date")
            return

    result = sync_artifacts(project_dir)
    click.echo(f"✓ Synced {result.artifacts_installed} artifacts, {result.hooks_installed} hooks")

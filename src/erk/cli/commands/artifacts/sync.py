"""Artifact sync command."""

import click

from erk.artifacts.staleness import check_staleness
from erk.artifacts.sync import sync_artifacts
from erk.core.context import ErkContext
from erk.core.repo_discovery import in_erk_repo


@click.command()
@click.option("--force", is_flag=True, help="Sync even if up to date")
@click.pass_obj
def sync(ctx: ErkContext, force: bool) -> None:
    """Sync erk artifacts to project."""
    project_dir = ctx.cwd

    if in_erk_repo(project_dir):
        click.echo("Dev mode - artifacts read from source, nothing to sync")
        return

    if not force:
        result = check_staleness(project_dir)
        if not result.is_stale:
            click.echo("Artifacts are up to date")
            return

    result = sync_artifacts(project_dir)
    click.echo(f"✓ Synced {result.artifacts_installed} artifacts, {result.hooks_installed} hooks")

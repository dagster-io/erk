"""Sync artifacts from erk package to project."""

from pathlib import Path

import click

from erk.artifacts.sync import sync_artifacts


@click.command("sync")
@click.option("-f", "--force", is_flag=True, help="Force sync even if up to date")
def sync_cmd(force: bool) -> None:
    """Sync artifacts from erk package to .claude/ directory.

    Copies bundled artifacts (commands, skills, agents, docs) from the
    installed erk package to the current project's .claude/ directory.

    When running in the erk repo itself, this is a no-op since artifacts
    are read directly from source.

    Examples:

    \b
      # Sync artifacts
      erk artifact sync

    \b
      # Force re-sync even if up to date
      erk artifact sync --force
    """
    project_dir = Path.cwd()

    result = sync_artifacts(project_dir, force)

    if result.success:
        click.echo(click.style("✓ ", fg="green") + result.message)
    else:
        click.echo(click.style("✗ ", fg="red") + result.message, err=True)
        raise SystemExit(1)

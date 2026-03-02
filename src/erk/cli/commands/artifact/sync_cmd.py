"""Sync artifacts from erk package to project."""

from pathlib import Path

import click

from erk.artifacts.state import load_installed_capabilities
from erk.artifacts.sync import (
    ArtifactSyncConfig,
    add_missing_gitignore_entries,
    find_missing_gitignore_entries,
    sync_artifacts,
)


@click.command("sync")
@click.option("-f", "--force", is_flag=True, help="Force sync even if up to date")
@click.pass_context
def sync_cmd(ctx: click.Context, force: bool) -> None:
    """Sync artifacts from erk package to .claude/ directory.

    Copies bundled artifacts (commands, skills, agents, docs) from the
    installed erk package to the current project's .claude/ directory.
    Also checks for missing .gitignore entries and offers to add them.

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
    package = ctx.obj.package_info
    config = ArtifactSyncConfig(
        package=package,
        installed_capabilities=load_installed_capabilities(project_dir),
        sync_capabilities=True,
        backend="claude",
    )

    result = sync_artifacts(project_dir, force, config=config)

    if result.success:
        click.echo(click.style("✓ ", fg="green") + result.message)
        if result.artifacts_removed > 0:
            click.echo(
                click.style("  ", fg="yellow")
                + f"Removed {result.artifacts_removed} orphaned artifact(s)"
            )
    else:
        click.echo(click.style("✗ ", fg="red") + result.message, err=True)
        raise SystemExit(1)

    # Check for missing gitignore entries
    missing = find_missing_gitignore_entries(project_dir)
    if missing:
        click.echo(f"\nMissing .gitignore entries: {', '.join(missing)}")
        if click.confirm("Add missing entries to .gitignore?", default=True):
            add_missing_gitignore_entries(project_dir, missing)
            click.echo(click.style("✓ ", fg="green") + "Updated .gitignore")

"""Sync artifacts from erk package to project."""

from pathlib import Path

import click

from erk.artifacts.state import load_installed_capabilities
from erk.artifacts.sync import (
    ArtifactSyncConfig,
    add_missing_gitignore_entries,
    delete_orphaned_artifacts,
    find_missing_gitignore_entries,
    sync_artifacts,
)


@click.command("sync")
@click.option("-f", "--force", is_flag=True, help="Force sync even if up to date")
@click.option("--dry-run", is_flag=True, help="Preview orphan removals without deleting")
@click.pass_context
def sync_cmd(ctx: click.Context, force: bool, dry_run: bool) -> None:
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

    \b
      # Preview what would be removed
      erk artifact sync --dry-run
    """
    project_dir = Path.cwd()
    package = ctx.obj.package_info
    config = ArtifactSyncConfig(
        package=package,
        installed_capabilities=load_installed_capabilities(project_dir),
        sync_capabilities=not dry_run,
        backend="claude",
        skip_skills=False,
    )

    result = sync_artifacts(project_dir, force, config=config)

    if not result.success:
        click.echo(click.style("✗ ", fg="red") + result.message, err=True)
        raise SystemExit(1)

    click.echo(click.style("✓ ", fg="green") + result.message)

    # Handle orphaned artifacts
    if result.orphans:
        click.echo(f"\nFound {len(result.orphans)} orphaned artifact(s):")
        for orphan in result.orphans:
            click.echo(f"  {orphan.path}")

        if dry_run:
            click.echo("\nDry run: no files were removed.")
        elif click.confirm(
            f"\nRemove these {len(result.orphans)} orphaned artifact(s)?", default=True
        ):
            removed = delete_orphaned_artifacts(list(result.orphans))
            click.echo(click.style("✓ ", fg="green") + f"Removed {removed} orphaned artifact(s)")

    if dry_run:
        return

    # Check for missing gitignore entries
    missing = find_missing_gitignore_entries(project_dir)
    if missing:
        click.echo(f"\nMissing .gitignore entries: {', '.join(missing)}")
        if click.confirm("Add missing entries to .gitignore?", default=True):
            add_missing_gitignore_entries(project_dir, missing)
            click.echo(click.style("✓ ", fg="green") + "Updated .gitignore")

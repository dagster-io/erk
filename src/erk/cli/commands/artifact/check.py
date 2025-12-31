"""Check artifact sync status."""

from pathlib import Path

import click

from erk.artifacts.artifact_health import find_missing_artifacts, find_orphaned_artifacts
from erk.artifacts.discovery import discover_artifacts
from erk.artifacts.staleness import check_staleness


def _display_orphan_warnings(orphans: dict[str, list[str]]) -> None:
    """Display orphan warnings with remediation commands."""
    total_orphans = sum(len(files) for files in orphans.values())
    click.echo(click.style("⚠️  ", fg="yellow") + f"Found {total_orphans} orphaned artifact(s)")
    click.echo("   Orphaned files (not in current erk package):")
    for folder, files in sorted(orphans.items()):
        click.echo(f"     {folder}/:")
        for filename in sorted(files):
            click.echo(f"       - {filename}")

    click.echo("")
    click.echo("   To remove:")
    for folder, files in sorted(orphans.items()):
        for filename in sorted(files):
            # Workflows are in .github/, not .claude/
            if folder.startswith(".github"):
                click.echo(f"     rm {folder}/{filename}")
            else:
                click.echo(f"     rm .claude/{folder}/{filename}")


def _display_missing_warnings(missing: dict[str, list[str]]) -> None:
    """Display missing artifact warnings."""
    total_missing = sum(len(files) for files in missing.values())
    click.echo(click.style("⚠️  ", fg="yellow") + f"Found {total_missing} missing artifact(s)")
    click.echo("   Missing from project:")
    for folder, files in sorted(missing.items()):
        click.echo(f"     {folder}:")
        for filename in sorted(files):
            click.echo(f"       - {filename}")
    click.echo("")
    click.echo("   Run 'erk artifact sync' to install missing artifacts")


def _display_installed_artifacts(project_dir: Path) -> None:
    """Display list of artifacts actually installed in project."""
    artifacts = discover_artifacts(project_dir)

    if not artifacts:
        click.echo("   (no artifacts installed)")
        return

    for artifact in artifacts:
        # Format based on artifact type
        if artifact.artifact_type == "command":
            # Commands can be namespaced (local:foo) or top-level (foo)
            if ":" in artifact.name:
                namespace, name = artifact.name.split(":", 1)
                click.echo(f"   commands/{namespace}/{name}.md")
            else:
                click.echo(f"   commands/{artifact.name}.md")
        elif artifact.artifact_type == "skill":
            click.echo(f"   skills/{artifact.name}")
        elif artifact.artifact_type == "agent":
            click.echo(f"   agents/{artifact.name}")
        elif artifact.artifact_type == "workflow":
            click.echo(f"   .github/workflows/{artifact.name}.yml")
        elif artifact.artifact_type == "hook":
            click.echo(f"   hooks/{artifact.name} (settings.json)")


@click.command("check")
def check_cmd() -> None:
    """Check if artifacts are in sync with erk version.

    Compares the version recorded in .erk/state.toml against
    the currently installed erk package version. Also checks
    for orphaned files that should be removed.

    Examples:

    \b
      # Check sync status
      erk artifact check
    """
    project_dir = Path.cwd()

    staleness_result = check_staleness(project_dir)
    orphan_result = find_orphaned_artifacts(project_dir)
    missing_result = find_missing_artifacts(project_dir)

    has_errors = False

    # Check staleness
    if staleness_result.reason == "erk-repo":
        click.echo(click.style("✓ ", fg="green") + "Development mode (artifacts read from source)")
        _display_installed_artifacts(project_dir)
    elif staleness_result.reason == "not-initialized":
        click.echo(click.style("⚠️  ", fg="yellow") + "Artifacts not initialized")
        click.echo(f"   Current erk version: {staleness_result.current_version}")
        click.echo("   Run 'erk artifact sync' to initialize")
        has_errors = True
    elif staleness_result.reason == "version-mismatch":
        click.echo(click.style("⚠️  ", fg="yellow") + "Artifacts out of sync")
        click.echo(f"   Installed version: {staleness_result.installed_version}")
        click.echo(f"   Current erk version: {staleness_result.current_version}")
        click.echo("   Run 'erk artifact sync' to update")
        has_errors = True
    else:
        click.echo(
            click.style("✓ ", fg="green")
            + f"Artifacts up to date (v{staleness_result.current_version})"
        )
        _display_installed_artifacts(project_dir)

    # Check for orphans (skip if erk-repo or no-claude-dir)
    if orphan_result.skipped_reason is None:
        if orphan_result.orphans:
            _display_orphan_warnings(orphan_result.orphans)
            has_errors = True
        else:
            click.echo(click.style("✓ ", fg="green") + "No orphaned artifacts")

    # Check for missing artifacts (skip if erk-repo or no-claude-dir)
    if missing_result.skipped_reason is None:
        if missing_result.missing:
            _display_missing_warnings(missing_result.missing)
            has_errors = True
        else:
            click.echo(click.style("✓ ", fg="green") + "No missing artifacts")

    if has_errors:
        raise SystemExit(1)

"""Check artifact sync status."""

from pathlib import Path

import click

from erk.artifacts.orphans import BUNDLED_AGENTS, BUNDLED_SKILLS, find_orphaned_artifacts
from erk.artifacts.staleness import check_staleness
from erk.artifacts.sync import get_bundled_claude_dir


def _display_orphan_warnings(orphans: dict[str, list[str]]) -> None:
    """Display orphan warnings with remediation commands."""
    total_orphans = sum(len(files) for files in orphans.values())
    click.echo(
        click.style("⚠️  ", fg="yellow") + f"Found {total_orphans} orphaned artifact(s) in .claude/"
    )
    click.echo("   Orphaned files (not in current erk package):")
    for folder, files in sorted(orphans.items()):
        click.echo(f"     {folder}/:")
        for filename in sorted(files):
            click.echo(f"       - {filename}")

    click.echo("")
    click.echo("   To remove:")
    for folder, files in sorted(orphans.items()):
        for filename in sorted(files):
            click.echo(f"     rm .claude/{folder}/{filename}")


def _display_bundled_artifacts() -> None:
    """Display list of bundled artifacts."""
    bundled_dir = get_bundled_claude_dir()
    artifacts: list[str] = []

    # Collect agents
    for agent in sorted(BUNDLED_AGENTS):
        artifacts.append(f"agents/{agent}")

    # Collect commands
    commands_dir = bundled_dir / "commands" / "erk"
    if commands_dir.exists():
        for cmd_file in sorted(commands_dir.iterdir()):
            if cmd_file.is_file() and cmd_file.suffix == ".md":
                artifacts.append(f"commands/erk/{cmd_file.name}")

    # Collect skills
    for skill in sorted(BUNDLED_SKILLS):
        artifacts.append(f"skills/{skill}")

    for artifact in artifacts:
        click.echo(f"   {artifact}")


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

    has_errors = False

    # Check staleness
    if staleness_result.reason == "erk-repo":
        click.echo(click.style("✓ ", fg="green") + "Development mode (artifacts read from source)")
        _display_bundled_artifacts()
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
        _display_bundled_artifacts()

    # Check for orphans (skip if erk-repo or no-claude-dir)
    if orphan_result.skipped_reason is None:
        if orphan_result.orphans:
            _display_orphan_warnings(orphan_result.orphans)
            has_errors = True
        else:
            click.echo(click.style("✓ ", fg="green") + "No orphaned artifacts")

    if has_errors:
        raise SystemExit(1)

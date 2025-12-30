"""Check artifact sync status."""

from pathlib import Path

import click

from erk.artifacts.staleness import check_staleness


@click.command("check")
def check_cmd() -> None:
    """Check if artifacts are in sync with erk version.

    Compares the version recorded in .erk/state.toml against
    the currently installed erk package version.

    Examples:

    \b
      # Check sync status
      erk artifact check
    """
    project_dir = Path.cwd()

    result = check_staleness(project_dir)

    if result.reason == "not-initialized":
        click.echo(click.style("⚠️  ", fg="yellow") + "Artifacts not initialized")
        click.echo(f"   Current erk version: {result.current_version}")
        click.echo("   Run 'erk artifact sync' to initialize")
        raise SystemExit(1)
    elif result.reason == "version-mismatch":
        click.echo(click.style("⚠️  ", fg="yellow") + "Artifacts out of sync")
        click.echo(f"   Installed version: {result.installed_version}")
        click.echo(f"   Current erk version: {result.current_version}")
        click.echo("   Run 'erk artifact sync' to update")
        raise SystemExit(1)
    else:
        click.echo(
            click.style("✓ ", fg="green") + f"Artifacts up to date (v{result.current_version})"
        )

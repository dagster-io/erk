"""Release notes command for viewing changelog entries.

Provides the `erk info release-notes` command for viewing changelog
entries on demand.
"""

import click

from erk.core.release_notes import (
    get_current_version,
    get_release_for_version,
    get_releases,
)


def _format_release(release_version: str, release_date: str | None, items: list[str]) -> None:
    """Format and display a single release entry."""
    header = f"[{release_version}]"
    if release_date:
        header += f" - {release_date}"

    click.echo(click.style(header, bold=True))
    click.echo()

    if items:
        for item in items:
            click.echo(f"  - {item}")
    else:
        click.echo(click.style("  (no entries)", dim=True))

    click.echo()


@click.command("release-notes")
@click.option("--all", "show_all", is_flag=True, help="Show all releases, not just current version")
@click.option(
    "--version",
    "-v",
    "target_version",
    help="Show notes for a specific version",
)
def release_notes_cmd(show_all: bool, target_version: str | None) -> None:
    """View erk release notes.

    Shows changelog entries for the current version by default.
    Use --all to see all releases, or --version to see a specific version.

    Examples:

    \b
      # Show current version notes
      erk info release-notes

      # Show all releases
      erk info release-notes --all

      # Show specific version
      erk info release-notes --version 0.2.1
    """
    releases = get_releases()

    if not releases:
        click.echo(click.style("No changelog found.", fg="yellow"))
        return

    if target_version:
        release = get_release_for_version(target_version)
        if release is None:
            click.echo(click.style(f"Version {target_version} not found in changelog.", fg="red"))
            return
        _format_release(release.version, release.date, release.items)
        return

    if show_all:
        click.echo(click.style("# erk Changelog", bold=True))
        click.echo()
        for release in releases:
            if release.version != "Unreleased" or release.items:
                _format_release(release.version, release.date, release.items)
        return

    # Default: show current version
    current = get_current_version()
    release = get_release_for_version(current)

    if release is None:
        click.echo(click.style(f"No notes found for version {current}.", dim=True))
        click.echo("Run 'erk info release-notes --all' to see all releases.")
        return

    click.echo(click.style(f"Release notes for erk {current}", bold=True))
    click.echo()
    _format_release(release.version, release.date, release.items)

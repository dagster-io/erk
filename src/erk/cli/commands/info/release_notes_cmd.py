"""Release notes command for viewing changelog entries.

Provides the `erk info release-notes` command for viewing changelog
entries on demand.
"""

import click

from erk.core.release_notes import (
    ReleaseEntry,
    get_current_version,
    get_release_for_version,
    get_releases,
)


def _format_items(items: list[tuple[str, int]]) -> None:
    """Format and display a list of release note items."""
    for item_text, indent_level in items:
        # Base indent (4 spaces) + extra indent per nesting level (2 spaces)
        indent = "    " + ("  " * indent_level)
        click.echo(f"{indent}- {item_text}")


def _format_release(release: ReleaseEntry) -> None:
    """Format and display a single release entry."""
    header = f"[{release.version}]"
    if release.date:
        header += f" - {release.date}"

    click.echo(click.style(header, bold=True))
    click.echo()

    if not release.categories and not release.items:
        click.echo(click.style("  (no entries)", dim=True))
        click.echo()
        return

    # If there are no categories but there are items, render them directly
    # This handles releases with just "- Initial release" without category headers
    if not release.categories and release.items:
        _format_items(release.items)
        click.echo()
        return

    # Render Major Changes first if present (with bold header)
    if "Major Changes" in release.categories:
        click.echo(click.style("  Major Changes", bold=True))
        _format_items(release.categories["Major Changes"])
        click.echo()

    # Then render standard sections in order
    standard_sections = ["Added", "Changed", "Fixed", "Removed"]
    for category in standard_sections:
        if category in release.categories:
            click.echo(f"  {category}")
            _format_items(release.categories[category])
            click.echo()

    # Render any remaining categories not in the standard list
    rendered = {"Major Changes"} | set(standard_sections)
    for category, items in release.categories.items():
        if category not in rendered:
            click.echo(f"  {category}")
            _format_items(items)
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
        _format_release(release)
        return

    if show_all:
        click.echo(click.style("# erk Changelog", bold=True))
        click.echo()
        for release in releases:
            if release.version != "Unreleased" or release.items:
                _format_release(release)
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
    _format_release(release)

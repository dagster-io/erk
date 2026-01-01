"""Project upgrade command - update repository to new erk version.

This command updates a repository to a new erk version:
- Updates the required version file to the installed version
- Force-syncs all artifacts
- Shows release notes between old and new versions
"""

import sys

import click

from erk.artifacts.sync import sync_artifacts
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.release_notes import (
    ReleaseEntry,
    get_current_version,
    get_releases,
)
from erk.core.version_check import get_required_version, write_required_version
from erk_shared.output.output import user_output


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a semantic version string into a tuple of integers.

    Args:
        version: Version string (e.g., "0.2.4")

    Returns:
        Tuple of integers (e.g., (0, 2, 4))
    """
    return tuple(int(part) for part in version.split("."))


def _get_releases_between(old_version: str, new_version: str) -> list[ReleaseEntry]:
    """Get release entries between two versions (exclusive of old, inclusive of new).

    Args:
        old_version: The older version string
        new_version: The newer version string

    Returns:
        List of ReleaseEntry objects between the versions
    """
    releases = get_releases()
    result: list[ReleaseEntry] = []

    old_parsed = _parse_version(old_version)
    new_parsed = _parse_version(new_version)

    for release in releases:
        if release.version == "Unreleased":
            continue

        release_parsed = _parse_version(release.version)

        # Include releases newer than old_version and up to new_version
        if old_parsed < release_parsed <= new_parsed:
            result.append(release)

    return result


def _display_release_notes(releases: list[ReleaseEntry]) -> None:
    """Display release notes to stderr.

    Args:
        releases: List of release entries to display
    """
    if not releases:
        return

    click.echo(file=sys.stderr)
    click.echo(click.style("  Release Notes", bold=True), file=sys.stderr)
    click.echo(click.style("  " + "─" * 50, dim=True), file=sys.stderr)
    click.echo(file=sys.stderr)

    for release in releases:
        if not release.items:
            continue

        header = f"  [{release.version}]"
        if release.date:
            header += f" - {release.date}"
        click.echo(click.style(header, bold=True), file=sys.stderr)

        if release.categories:
            for category, category_items in release.categories.items():
                if not category_items:
                    continue
                click.echo(click.style(f"    {category}", dim=True), file=sys.stderr)
                for item_text, indent_level in category_items:
                    indent = "      " + ("  " * indent_level)
                    click.echo(f"{indent}• {item_text}", file=sys.stderr)
        else:
            for item_text, indent_level in release.items:
                indent = "    " + ("  " * indent_level)
                click.echo(f"{indent}• {item_text}", file=sys.stderr)
        click.echo(file=sys.stderr)

    click.echo(click.style("  " + "─" * 50, dim=True), file=sys.stderr)
    click.echo(file=sys.stderr)


@click.command("upgrade")
@click.option(
    "--force",
    is_flag=True,
    help="Force upgrade even if versions match.",
)
@click.pass_obj
def upgrade_cmd(ctx: ErkContext, force: bool) -> None:
    """Upgrade repository to the currently installed erk version.

    This command updates the repository's erk configuration:

    - Updates .erk/required-erk-uv-tool-version to your installed version
    - Force-syncs all artifacts (skills, commands, agents, workflows)
    - Shows release notes for versions between old and new

    After upgrading, commit and push the changes. Team members will be
    prompted to run 'uv tool upgrade erk' when their version mismatches.

    Example:
        erk project upgrade
    """
    # Discover repo context
    repo_context = discover_repo_context(ctx, ctx.cwd)

    # Check if repo is erk-ified
    erk_dir = repo_context.root / ".erk"
    if not erk_dir.exists():
        user_output(click.style("Error: ", fg="red") + "Repository not erk-ified.")
        user_output("Run 'erk project init' first to set up erk for this repository.")
        raise SystemExit(1)

    # Get current versions
    installed_version = get_current_version()
    required_version = get_required_version(repo_context.root)

    if required_version is None:
        user_output(click.style("Warning: ", fg="yellow") + "No required version file found.")
        user_output("Creating version file...")
        old_version = "0.0.0"  # Sentinel for "no previous version"
    else:
        old_version = required_version

    # Check if upgrade is needed
    if installed_version == required_version and not force:
        user_output(f"Repository already at version {installed_version}")
        user_output("Use --force to re-sync artifacts anyway.")
        return

    # Show what we're doing
    if required_version is not None:
        user_output(f"Upgrading from {required_version} to {installed_version}")
    else:
        user_output(f"Setting required version to {installed_version}")

    # Update version file
    write_required_version(repo_context.root, installed_version)
    user_output(click.style("✓ ", fg="green") + f"Updated required version to {installed_version}")

    # Force-sync artifacts
    sync_result = sync_artifacts(repo_context.root, force=True)
    if sync_result.success:
        user_output(click.style("✓ ", fg="green") + sync_result.message)
    else:
        user_output(click.style("⚠ ", fg="yellow") + f"Artifact sync failed: {sync_result.message}")
        user_output("  Run 'erk artifact sync' to retry")

    # Show release notes if upgrading from a known version
    if required_version is not None and required_version != installed_version:
        releases = _get_releases_between(old_version, installed_version)
        if releases:
            _display_release_notes(releases)

    user_output("")
    user_output(click.style("✓ ", fg="green") + "Upgrade complete!")
    user_output("")
    user_output("Next steps:")
    user_output("  1. Review and commit the changes to .erk/ and .claude/")
    user_output("  2. Push to remote - team members will be prompted to upgrade")

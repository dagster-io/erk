"""Update CHANGELOG.md with new release notes."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import click

from erk_dev.commands.bump_version.command import find_repo_root


def insert_release_notes(
    *, changelog_path: Path, version: str, date: str, notes: str, dry_run: bool
) -> bool:
    """Insert release notes into CHANGELOG.md under a new version header.

    Transforms:
        ## [Unreleased]
        <existing unreleased content>
        ## [X.Y.Z] - YYYY-MM-DD

    Into:
        ## [Unreleased]
        ## [NEW_VERSION] - DATE
        <notes>
        ## [X.Y.Z] - YYYY-MM-DD

    Returns True if successful, False if changelog not found or invalid.
    """
    if not changelog_path.exists():
        return False

    content = changelog_path.read_text(encoding="utf-8")

    if "## [Unreleased]" not in content:
        return False

    # Pattern: [Unreleased] followed by content until next version header
    pattern = r"(## \[Unreleased\])\n(.*?)(## \[\d)"
    match = re.search(pattern, content, re.DOTALL)

    if match is None:
        # Handle case where [Unreleased] is at end of file
        simple_pattern = r"(## \[Unreleased\])\n(.*?)$"
        match = re.search(simple_pattern, content, re.DOTALL)
        if match is None:
            return False

        # Insert new version section after [Unreleased]
        new_section = f"## [Unreleased]\n\n## [{version}] - {date}\n\n{notes.strip()}\n"
        new_content = re.sub(simple_pattern, new_section, content, flags=re.DOTALL)
    else:
        next_version_start = match.group(3)

        # Insert new version between [Unreleased] and previous version
        new_section = (
            f"## [Unreleased]\n\n## [{version}] - {date}\n\n{notes.strip()}\n\n{next_version_start}"
        )
        new_content = re.sub(pattern, new_section, content, flags=re.DOTALL)

    if not dry_run:
        changelog_path.write_text(new_content, encoding="utf-8")
    return True


@click.command("release-update")
@click.option("--version", "version", required=True, help="Version number (e.g., 0.2.2)")
@click.option(
    "--notes-file",
    "notes_file",
    type=click.Path(exists=True),
    help="Path to file containing release notes",
)
@click.option("--notes", "notes_text", help="Release notes as text (alternative to --notes-file)")
@click.option("--date", "date_str", help="Release date/time (YYYY-MM-DD HH:MM PT)")
@click.option("--dry-run", is_flag=True, help="Show what would change without modifying files")
def release_update_command(
    *,
    version: str,
    notes_file: str | None,
    notes_text: str | None,
    date_str: str | None,
    dry_run: bool,
) -> None:
    """Update CHANGELOG.md with new release notes.

    Inserts a new version section after [Unreleased] with the provided notes.
    Either --notes-file or --notes must be provided.
    """
    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise click.ClickException(f"Invalid version format: {version}. Expected X.Y.Z")

    # Get notes content
    if notes_file:
        notes = Path(notes_file).read_text(encoding="utf-8")
    elif notes_text:
        # Handle escaped newlines from command line
        notes = notes_text.replace("\\n", "\n")
    else:
        raise click.ClickException("Either --notes-file or --notes must be provided")

    # Get date/time in Pacific Time
    pacific = ZoneInfo("America/Los_Angeles")
    date = date_str or datetime.now(pacific).strftime("%Y-%m-%d %H:%M PT")

    # Validate date format
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} PT$", date):
        raise click.ClickException(f"Invalid date format: {date}. Expected YYYY-MM-DD HH:MM PT")

    # Find repo root and changelog
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise click.ClickException("Could not find repository root")

    changelog_path = repo_root / "CHANGELOG.md"

    if dry_run:
        click.echo(f"[DRY RUN] Would update {changelog_path}")
        click.echo(f"  Version: {version}")
        click.echo(f"  Date: {date}")
        click.echo(f"  Notes preview: {notes[:100]}...")
    else:
        success = insert_release_notes(
            changelog_path=changelog_path,
            version=version,
            date=date,
            notes=notes,
            dry_run=False,
        )
        if success:
            click.echo(f"Updated CHANGELOG.md with version {version}")
        else:
            raise click.ClickException(
                "Failed to update CHANGELOG.md. Ensure [Unreleased] section exists."
            )

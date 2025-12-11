"""Release notes management for erk.

Provides functionality for:
- Parsing CHANGELOG.md into structured data
- Detecting version changes since last run
- Displaying upgrade banners
"""

import importlib.metadata
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path


@dataclass
class ReleaseEntry:
    """A single release entry from the changelog."""

    version: str
    date: str | None
    content: str
    items: list[str] = field(default_factory=list)


@cache
def _changelog_path() -> Path:
    """Get the path to the bundled CHANGELOG.md.

    Returns:
        Path to CHANGELOG.md bundled with the package
    """
    return Path(__file__).parent.parent / "data" / "CHANGELOG.md"


@cache
def _last_seen_version_path() -> Path:
    """Get the path to the last seen version file.

    Returns:
        Path to ~/.erk/last_seen_version
    """
    return Path.home() / ".erk" / "last_seen_version"


def get_current_version() -> str:
    """Get the currently installed version of erk.

    Returns:
        Version string (e.g., "0.2.1")
    """
    return importlib.metadata.version("erk")


def get_last_seen_version() -> str | None:
    """Get the last version the user was notified about.

    Returns:
        Version string if tracking file exists, None otherwise
    """
    path = _last_seen_version_path()
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def update_last_seen_version(version: str) -> None:
    """Update the last seen version tracking file.

    Args:
        version: Version string to record
    """
    path = _last_seen_version_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version, encoding="utf-8")


def parse_changelog(content: str) -> list[ReleaseEntry]:
    """Parse CHANGELOG.md content into structured release entries.

    Args:
        content: Raw markdown content of CHANGELOG.md

    Returns:
        List of ReleaseEntry objects, one per version section
    """
    entries: list[ReleaseEntry] = []

    # Match version headers like "## [0.2.1] - 2025-12-11" or "## [Unreleased]"
    version_pattern = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?", re.MULTILINE)

    matches = list(version_pattern.finditer(content))

    for i, match in enumerate(matches):
        version = match.group(1)
        date = match.group(2)

        # Extract content between this header and the next
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()

        # Extract bullet items from content
        items: list[str] = []
        for line in section_content.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                items.append(line[2:])

        entries.append(
            ReleaseEntry(
                version=version,
                date=date,
                content=section_content,
                items=items,
            )
        )

    return entries


def get_changelog_content() -> str | None:
    """Read the bundled CHANGELOG.md content.

    Returns:
        Changelog content if file exists, None otherwise
    """
    path = _changelog_path()
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def get_releases() -> list[ReleaseEntry]:
    """Get all release entries from the bundled changelog.

    Returns:
        List of ReleaseEntry objects, empty if changelog not found
    """
    content = get_changelog_content()
    if content is None:
        return []
    return parse_changelog(content)


def get_release_for_version(version: str) -> ReleaseEntry | None:
    """Get the release entry for a specific version.

    Args:
        version: Version string to look up

    Returns:
        ReleaseEntry if found, None otherwise
    """
    releases = get_releases()
    for release in releases:
        if release.version == version:
            return release
    return None


def check_for_version_change() -> tuple[bool, list[ReleaseEntry]]:
    """Check if the version has changed since last run.

    Returns:
        Tuple of (changed: bool, new_releases: list[ReleaseEntry])
        where new_releases contains all releases newer than last seen
    """
    current = get_current_version()
    last_seen = get_last_seen_version()

    # First run - no notification needed, just update tracking
    if last_seen is None:
        update_last_seen_version(current)
        return (False, [])

    # No change
    if current == last_seen:
        return (False, [])

    # Version changed - find all releases between last_seen and current
    releases = get_releases()
    new_releases: list[ReleaseEntry] = []

    for release in releases:
        # Skip unreleased section
        if release.version == "Unreleased":
            continue
        # Stop at last seen version
        if release.version == last_seen:
            break
        new_releases.append(release)

    # Update tracking file
    update_last_seen_version(current)

    return (True, new_releases)

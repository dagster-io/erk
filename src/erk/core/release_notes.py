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

from erk_shared.gateway.erk_installation.abc import ErkInstallation


@dataclass
class ReleaseEntry:
    """A single release entry from the changelog.

    Items are stored as tuples of (text, indent_level) where indent_level
    is 0 for top-level bullets, 1 for first nesting level, etc.
    """

    version: str
    date: str | None
    content: str
    items: list[tuple[str, int]] = field(default_factory=list)
    categories: dict[str, list[tuple[str, int]]] = field(default_factory=dict)


@cache
def _changelog_path() -> Path | None:
    """Get the path to CHANGELOG.md.

    In development, reads from repo root. In installed package, reads from bundled data dir.

    Returns:
        Path to CHANGELOG.md if found, None otherwise
    """
    # Bundled location (installed package via force-include)
    bundled = Path(__file__).parent.parent / "data" / "CHANGELOG.md"
    if bundled.exists():
        return bundled

    # Development fallback: repo root (3 levels up from src/erk/core/)
    dev_root = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
    if dev_root.exists():
        return dev_root

    return None


def get_current_version() -> str:
    """Get the currently installed version of erk.

    Returns:
        Version string (e.g., "0.2.1")
    """
    return importlib.metadata.version("erk")


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a semantic version string into a tuple of integers.

    Args:
        version: Version string (e.g., "0.2.4")

    Returns:
        Tuple of integers (e.g., (0, 2, 4))
    """
    return tuple(int(part) for part in version.split("."))


def _is_upgrade(current: str, last_seen: str) -> bool:
    """Check if current version is newer than last_seen version.

    Args:
        current: Current version string
        last_seen: Previously seen version string

    Returns:
        True if current is a newer version than last_seen
    """
    return _parse_version(current) > _parse_version(last_seen)


def get_last_seen_version(erk_installation: ErkInstallation) -> str | None:
    """Get the last version the user was notified about.

    Args:
        erk_installation: ErkInstallation gateway for accessing ~/.erk/

    Returns:
        Version string if tracking file exists, None otherwise
    """
    return erk_installation.get_last_seen_version()


def update_last_seen_version(erk_installation: ErkInstallation, version: str) -> None:
    """Update the last seen version tracking file.

    Args:
        erk_installation: ErkInstallation gateway for accessing ~/.erk/
        version: Version string to record
    """
    erk_installation.update_last_seen_version(version)


def parse_changelog(content: str) -> list[ReleaseEntry]:
    """Parse CHANGELOG.md content into structured release entries.

    Args:
        content: Raw markdown content of CHANGELOG.md

    Returns:
        List of ReleaseEntry objects, one per version section
    """
    entries: list[ReleaseEntry] = []

    # Match "## [0.2.1] - 2025-12-11" or "## [0.2.1] - 2025-12-11 14:30 PT" or "## [Unreleased]"
    version_pattern = re.compile(
        r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2} PT)?))?",
        re.MULTILINE,
    )

    matches = list(version_pattern.finditer(content))

    for i, match in enumerate(matches):
        version = match.group(1)
        date = match.group(2)

        # Extract content between this header and the next
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()

        # Extract bullet items grouped by category (### Added, ### Changed, etc.)
        # Items are stored as (text, indent_level) tuples to preserve nesting
        items: list[tuple[str, int]] = []
        categories: dict[str, list[tuple[str, int]]] = {}
        current_category: str | None = None

        for line in section_content.split("\n"):
            # Count leading spaces to detect nesting level
            stripped = line.lstrip()
            leading_spaces = len(line) - len(stripped)
            indent_level = leading_spaces // 2  # 2 spaces = 1 nesting level

            # Check for category header (### Added, ### Changed, ### Fixed, etc.)
            if stripped.startswith("### "):
                current_category = stripped[4:]
                categories[current_category] = []
            elif stripped.startswith("- "):
                item_text = stripped[2:]
                item_tuple = (item_text, indent_level)
                items.append(item_tuple)
                if current_category is not None:
                    categories[current_category].append(item_tuple)

        entries.append(
            ReleaseEntry(
                version=version,
                date=date,
                content=section_content,
                items=items,
                categories=categories,
            )
        )

    return entries


def get_changelog_content() -> str | None:
    """Read the CHANGELOG.md content.

    Returns:
        Changelog content if file exists, None otherwise
    """
    path = _changelog_path()
    if path is None:
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


def check_for_version_change(
    erk_installation: ErkInstallation,
) -> tuple[bool, list[ReleaseEntry]]:
    """Check if the version has changed since last run.

    Args:
        erk_installation: ErkInstallation gateway for accessing ~/.erk/

    Returns:
        Tuple of (changed: bool, new_releases: list[ReleaseEntry])
        where new_releases contains all releases newer than last seen
    """
    current = get_current_version()
    last_seen = get_last_seen_version(erk_installation)

    # First run - no notification needed, just update tracking
    if last_seen is None:
        update_last_seen_version(erk_installation, current)
        return (False, [])

    # No change
    if current == last_seen:
        return (False, [])

    # Only show banner for upgrades, not downgrades
    # This prevents repeated banners when switching between worktrees
    # with different erk versions installed
    if not _is_upgrade(current, last_seen):
        # Don't update tracking on downgrade - keep tracking the max version seen
        # This prevents repeated banners when switching between worktrees
        return (False, [])

    # Upgrade detected - find all releases between last_seen and current
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
    update_last_seen_version(erk_installation, current)

    return (True, new_releases)

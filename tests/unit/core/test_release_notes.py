"""Unit tests for release_notes.py changelog parsing and version tracking."""

from unittest.mock import patch

from erk.core.release_notes import (
    ReleaseEntry,
    _is_upgrade,
    _parse_version,
    check_for_version_change,
    parse_changelog,
)
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation

SAMPLE_CHANGELOG = """\
# Changelog

All notable changes to erk will be documented in this file.

## [Unreleased]

## [0.2.2] - 2025-12-15

### Added
- Added new feature X
- Added feature Y

### Fixed
- Fixed bug in Z

## [0.2.1] - 2025-12-11

Initial release with changelog tracking.

- Added release notes system with version change detection
- Added `erk release-notes` command for viewing changelog

## [0.2.0] - 2025-12-01

- Initial public release
"""


def test_parse_changelog_extracts_versions() -> None:
    """Test that parse_changelog extracts all version headers."""
    entries = parse_changelog(SAMPLE_CHANGELOG)

    versions = [e.version for e in entries]
    assert versions == ["Unreleased", "0.2.2", "0.2.1", "0.2.0"]


def test_parse_changelog_extracts_dates() -> None:
    """Test that parse_changelog extracts dates from version headers."""
    entries = parse_changelog(SAMPLE_CHANGELOG)

    # Unreleased has no date
    assert entries[0].date is None
    # Version 0.2.2 has a date
    assert entries[1].date == "2025-12-15"
    # Version 0.2.1 has a date
    assert entries[2].date == "2025-12-11"


def test_parse_changelog_extracts_items() -> None:
    """Test that parse_changelog extracts bullet items as (text, indent_level) tuples."""
    entries = parse_changelog(SAMPLE_CHANGELOG)

    # 0.2.2 has multiple bullet items, all at indent level 0 (top-level)
    assert len(entries[1].items) == 3
    assert entries[1].items[0] == ("Added new feature X", 0)
    assert entries[1].items[1] == ("Added feature Y", 0)
    assert entries[1].items[2] == ("Fixed bug in Z", 0)

    # 0.2.1 has 2 items
    assert len(entries[2].items) == 2

    # 0.2.0 has 1 item
    assert len(entries[3].items) == 1
    assert entries[3].items[0] == ("Initial public release", 0)


def test_parse_changelog_empty_unreleased() -> None:
    """Test that unreleased section can be empty."""
    entries = parse_changelog(SAMPLE_CHANGELOG)

    # Unreleased has no items
    assert entries[0].version == "Unreleased"
    assert entries[0].items == []


def test_parse_changelog_minimal() -> None:
    """Test parsing minimal changelog with only unreleased section."""
    minimal = """\
# Changelog

## [Unreleased]

## [0.1.0] - 2025-01-01

- Initial release
"""
    entries = parse_changelog(minimal)

    assert len(entries) == 2
    assert entries[0].version == "Unreleased"
    assert entries[1].version == "0.1.0"
    assert entries[1].items == [("Initial release", 0)]


def test_release_entry_dataclass() -> None:
    """Test ReleaseEntry dataclass structure."""
    entry = ReleaseEntry(
        version="1.0.0",
        date="2025-01-01",
        content="Some content",
        items=[("Item 1", 0), ("Item 2", 0)],
    )

    assert entry.version == "1.0.0"
    assert entry.date == "2025-01-01"
    assert entry.content == "Some content"
    assert entry.items == [("Item 1", 0), ("Item 2", 0)]


def test_release_entry_default_items() -> None:
    """Test ReleaseEntry items default to empty list."""
    entry = ReleaseEntry(version="1.0.0", date=None, content="")

    assert entry.items == []


NESTED_CHANGELOG = """\
# Changelog

## [1.0.0] - 2025-01-01

### Changed
- Parent item with sub-items:
  - First nested item
  - Second nested item
- Another top-level item
"""


def test_parse_changelog_preserves_nesting() -> None:
    """Test that parse_changelog preserves indentation levels for nested items."""
    entries = parse_changelog(NESTED_CHANGELOG)
    items = entries[0].items

    assert items[0] == ("Parent item with sub-items:", 0)
    assert items[1] == ("First nested item", 1)
    assert items[2] == ("Second nested item", 1)
    assert items[3] == ("Another top-level item", 0)


def test_parse_changelog_categories_preserve_nesting() -> None:
    """Test that categories also preserve indentation levels."""
    entries = parse_changelog(NESTED_CHANGELOG)
    changed_items = entries[0].categories["Changed"]

    assert changed_items[0] == ("Parent item with sub-items:", 0)
    assert changed_items[1] == ("First nested item", 1)
    assert changed_items[2] == ("Second nested item", 1)
    assert changed_items[3] == ("Another top-level item", 0)


def test_parse_version_simple() -> None:
    """Test parsing a simple semantic version."""
    assert _parse_version("0.2.4") == (0, 2, 4)


def test_parse_version_major_only() -> None:
    """Test parsing a version with major.minor.patch."""
    assert _parse_version("1.0.0") == (1, 0, 0)
    assert _parse_version("2.10.3") == (2, 10, 3)


def test_is_upgrade_returns_true_for_newer_version() -> None:
    """Test _is_upgrade returns True when current is newer."""
    assert _is_upgrade("0.2.4", "0.2.3") is True
    assert _is_upgrade("0.3.0", "0.2.9") is True
    assert _is_upgrade("1.0.0", "0.9.9") is True


def test_is_upgrade_returns_false_for_same_version() -> None:
    """Test _is_upgrade returns False when versions are equal."""
    assert _is_upgrade("0.2.4", "0.2.4") is False


def test_is_upgrade_returns_false_for_downgrade() -> None:
    """Test _is_upgrade returns False when current is older."""
    assert _is_upgrade("0.2.3", "0.2.4") is False
    assert _is_upgrade("0.2.9", "0.3.0") is False
    assert _is_upgrade("0.9.9", "1.0.0") is False


@patch("erk.core.release_notes.get_current_version")
def test_check_for_version_change_downgrade_preserves_max_version(
    mock_current: patch,
) -> None:
    """Test that downgrades don't update tracking (preserves max version seen)."""
    mock_current.return_value = "0.2.3"
    fake_installation = FakeErkInstallation(last_seen_version="0.2.4")

    changed, releases = check_for_version_change(fake_installation)

    assert changed is False
    assert releases == []
    # Verify version was NOT updated (downgrade should preserve max)
    assert fake_installation.version_updates == []


@patch("erk.core.release_notes.get_current_version")
def test_check_for_version_change_same_version_no_update(
    mock_current: patch,
) -> None:
    """Test that same version doesn't update tracking file."""
    mock_current.return_value = "0.2.4"
    fake_installation = FakeErkInstallation(last_seen_version="0.2.4")

    changed, releases = check_for_version_change(fake_installation)

    assert changed is False
    assert releases == []
    # Verify version was NOT updated (same version)
    assert fake_installation.version_updates == []


@patch("erk.core.release_notes.get_releases")
@patch("erk.core.release_notes.get_current_version")
def test_check_for_version_change_upgrade_shows_banner(
    mock_current: patch,
    mock_releases: patch,
) -> None:
    """Test that upgrades show banner and update tracking."""
    mock_current.return_value = "0.2.4"
    mock_releases.return_value = [
        ReleaseEntry(version="Unreleased", date=None, content=""),
        ReleaseEntry(version="0.2.4", date="2025-12-12", content="New feature"),
        ReleaseEntry(version="0.2.3", date="2025-12-11", content="Old feature"),
    ]
    fake_installation = FakeErkInstallation(last_seen_version="0.2.3")

    changed, releases = check_for_version_change(fake_installation)

    assert changed is True
    assert len(releases) == 1
    assert releases[0].version == "0.2.4"
    # Verify version was updated via the fake
    assert fake_installation.version_updates == ["0.2.4"]

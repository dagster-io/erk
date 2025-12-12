"""Unit tests for release_notes.py changelog parsing and version tracking."""

from erk.core.release_notes import (
    ReleaseEntry,
    parse_changelog,
)

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

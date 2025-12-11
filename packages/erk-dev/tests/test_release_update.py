"""Tests for release-update command."""

from pathlib import Path

from click.testing import CliRunner

from erk_dev.commands.release_update.command import (
    insert_release_notes,
    release_update_command,
)


def test_insert_release_notes_adds_version_section(tmp_path: Path) -> None:
    """Test that insert_release_notes adds new version after [Unreleased]."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

## [0.2.0] - 2025-12-01

- Previous release
""",
        encoding="utf-8",
    )

    notes = """\
### Added
- New feature X
- New feature Y

### Fixed
- Bug fix Z"""

    result = insert_release_notes(changelog, "0.2.1", "2025-12-11", notes, dry_run=False)

    assert result is True
    content = changelog.read_text(encoding="utf-8")
    assert "## [0.2.1] - 2025-12-11" in content
    assert "### Added" in content
    assert "- New feature X" in content
    assert "## [Unreleased]" in content
    # New version should be between [Unreleased] and [0.2.0]
    unreleased_pos = content.find("## [Unreleased]")
    new_version_pos = content.find("## [0.2.1]")
    old_version_pos = content.find("## [0.2.0]")
    assert unreleased_pos < new_version_pos < old_version_pos


def test_insert_release_notes_handles_unreleased_at_end(tmp_path: Path) -> None:
    """Test handling when [Unreleased] is at the end of file."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]
""",
        encoding="utf-8",
    )

    notes = "- Initial release"

    result = insert_release_notes(changelog, "0.1.0", "2025-01-01", notes, dry_run=False)

    assert result is True
    content = changelog.read_text(encoding="utf-8")
    assert "## [0.1.0] - 2025-01-01" in content
    assert "- Initial release" in content


def test_insert_release_notes_dry_run_does_not_modify(tmp_path: Path) -> None:
    """Test that dry_run=True doesn't modify the file."""
    changelog = tmp_path / "CHANGELOG.md"
    original = """\
# Changelog

## [Unreleased]

## [0.2.0] - 2025-12-01

- Previous release
"""
    changelog.write_text(original, encoding="utf-8")

    result = insert_release_notes(changelog, "0.2.1", "2025-12-11", "- New stuff", dry_run=True)

    assert result is True
    assert changelog.read_text(encoding="utf-8") == original


def test_insert_release_notes_returns_false_when_no_unreleased(tmp_path: Path) -> None:
    """Test that False is returned when no [Unreleased] section exists."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [0.2.0] - 2025-12-01

- Previous release
""",
        encoding="utf-8",
    )

    result = insert_release_notes(changelog, "0.2.1", "2025-12-11", "- New stuff", dry_run=False)

    assert result is False


def test_insert_release_notes_returns_false_when_no_file(tmp_path: Path) -> None:
    """Test that False is returned when changelog doesn't exist."""
    changelog = tmp_path / "CHANGELOG.md"

    result = insert_release_notes(changelog, "0.2.1", "2025-12-11", "- New stuff", dry_run=False)

    assert result is False


def test_release_update_command_with_notes_file(tmp_path: Path) -> None:
    """Test command with --notes-file option."""
    # Set up repo structure
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

## [0.2.0] - 2025-12-01

- Previous
""",
        encoding="utf-8",
    )

    notes_file = tmp_path / "notes.md"
    notes_file.write_text("### Added\n- Feature X\n", encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            release_update_command,
            ["--version", "0.2.1", "--notes-file", str(notes_file), "--date", "2025-12-11"],
        )

    assert result.exit_code == 0
    assert "Updated CHANGELOG.md with version 0.2.1" in result.output
    content = changelog.read_text(encoding="utf-8")
    assert "## [0.2.1] - 2025-12-11" in content


def test_release_update_command_with_notes_text(tmp_path: Path) -> None:
    """Test command with --notes option."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

## [0.2.0] - 2025-12-01

- Previous
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            release_update_command,
            ["--version", "0.2.1", "--notes", "### Added\\n- Feature X", "--date", "2025-12-11"],
        )

    assert result.exit_code == 0
    content = changelog.read_text(encoding="utf-8")
    assert "## [0.2.1] - 2025-12-11" in content
    assert "### Added" in content
    assert "- Feature X" in content


def test_release_update_command_validates_version_format(tmp_path: Path) -> None:
    """Test that invalid version format is rejected."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv.workspace]\nmembers = []\n", encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            release_update_command,
            ["--version", "invalid", "--notes", "test"],
        )

    assert result.exit_code != 0
    assert "Invalid version format" in result.output


def test_release_update_command_validates_date_format(tmp_path: Path) -> None:
    """Test that invalid date format is rejected."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv.workspace]\nmembers = []\n", encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            release_update_command,
            ["--version", "0.2.1", "--notes", "test", "--date", "12-11-2025"],
        )

    assert result.exit_code != 0
    assert "Invalid date format" in result.output


def test_release_update_command_requires_notes(tmp_path: Path) -> None:
    """Test that either --notes or --notes-file is required."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv.workspace]\nmembers = []\n", encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            release_update_command,
            ["--version", "0.2.1"],
        )

    assert result.exit_code != 0
    assert "Either --notes-file or --notes must be provided" in result.output

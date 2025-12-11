"""Tests for erk release-notes command.

These tests verify CLI output formatting. The parsing logic is tested
in tests/unit/core/test_release_notes.py.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.info.release_notes_cmd import release_notes_cmd

# Sample changelog content for testing
SAMPLE_CHANGELOG = """\
# Changelog

## [Unreleased]

### Added
- In progress feature

## [1.0.0] - 2025-12-11

### Added
- Feature X
- Feature Y

### Fixed
- Bug Z

## [0.9.0] - 2025-12-01

- Initial release
"""


def test_release_notes_shows_current_version(tmp_path: Path) -> None:
    """Test that release-notes shows current version notes by default."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE_CHANGELOG, encoding="utf-8")

    runner = CliRunner()

    with (
        patch("erk.core.release_notes._changelog_path", return_value=changelog),
        patch("erk.cli.commands.info.release_notes_cmd.get_current_version", return_value="1.0.0"),
    ):
        # Clear the cache so our patched path is used
        from erk.core.release_notes import _changelog_path

        _changelog_path.cache_clear()

        result = runner.invoke(release_notes_cmd, [])

    assert result.exit_code == 0
    assert "1.0.0" in result.output
    assert "Feature X" in result.output
    assert "Feature Y" in result.output


def test_release_notes_all_shows_all_releases(tmp_path: Path) -> None:
    """Test that --all flag shows all releases."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE_CHANGELOG, encoding="utf-8")

    runner = CliRunner()

    with patch("erk.core.release_notes._changelog_path", return_value=changelog):
        from erk.core.release_notes import _changelog_path

        _changelog_path.cache_clear()

        result = runner.invoke(release_notes_cmd, ["--all"])

    assert result.exit_code == 0
    assert "Changelog" in result.output
    assert "Unreleased" in result.output
    assert "1.0.0" in result.output
    assert "0.9.0" in result.output
    assert "Feature X" in result.output
    assert "Initial release" in result.output


def test_release_notes_version_flag(tmp_path: Path) -> None:
    """Test that --version flag shows specific version notes."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE_CHANGELOG, encoding="utf-8")

    runner = CliRunner()

    with patch("erk.core.release_notes._changelog_path", return_value=changelog):
        from erk.core.release_notes import _changelog_path

        _changelog_path.cache_clear()

        result = runner.invoke(release_notes_cmd, ["--version", "0.9.0"])

    assert result.exit_code == 0
    assert "0.9.0" in result.output
    assert "Initial release" in result.output


def test_release_notes_version_not_found(tmp_path: Path) -> None:
    """Test error handling for non-existent version."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE_CHANGELOG, encoding="utf-8")

    runner = CliRunner()

    with patch("erk.core.release_notes._changelog_path", return_value=changelog):
        from erk.core.release_notes import _changelog_path

        _changelog_path.cache_clear()

        result = runner.invoke(release_notes_cmd, ["--version", "99.99.99"])

    assert result.exit_code == 0
    assert "not found" in result.output


def test_release_notes_no_changelog(tmp_path: Path) -> None:
    """Test handling when no changelog is found."""
    # Point to non-existent file
    changelog = tmp_path / "CHANGELOG.md"

    runner = CliRunner()

    with patch("erk.core.release_notes._changelog_path", return_value=changelog):
        from erk.core.release_notes import _changelog_path

        _changelog_path.cache_clear()

        result = runner.invoke(release_notes_cmd, [])

    assert result.exit_code == 0
    assert "No changelog found" in result.output

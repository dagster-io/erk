"""Unit tests for version_check.py version comparison logic."""

from pathlib import Path

from erk.core.version_check import (
    format_version_warning,
    get_required_version,
    is_version_mismatch,
)


def test_get_required_version_returns_version_when_file_exists(tmp_path: Path) -> None:
    """Test that get_required_version reads version from file."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text("0.2.8\n", encoding="utf-8")

    result = get_required_version(tmp_path)

    assert result == "0.2.8"


def test_get_required_version_returns_none_when_file_missing(tmp_path: Path) -> None:
    """Test that get_required_version returns None when file doesn't exist."""
    result = get_required_version(tmp_path)

    assert result is None


def test_get_required_version_strips_whitespace(tmp_path: Path) -> None:
    """Test that get_required_version strips whitespace from version."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text("  0.2.8  \n", encoding="utf-8")

    result = get_required_version(tmp_path)

    assert result == "0.2.8"


def test_is_version_mismatch_returns_true_when_versions_differ() -> None:
    """Test is_version_mismatch returns True when versions don't match."""
    # Installed older than required
    assert is_version_mismatch("0.2.7", "0.2.8") is True
    assert is_version_mismatch("0.2.0", "0.3.0") is True
    # Installed newer than required
    assert is_version_mismatch("0.2.9", "0.2.8") is True
    assert is_version_mismatch("1.0.0", "0.2.8") is True


def test_is_version_mismatch_returns_false_when_versions_match() -> None:
    """Test is_version_mismatch returns False when versions match exactly."""
    assert is_version_mismatch("0.2.8", "0.2.8") is False
    assert is_version_mismatch("1.0.0", "1.0.0") is False


def test_format_version_warning_includes_both_versions() -> None:
    """Test that format_version_warning includes both version numbers."""
    result = format_version_warning("0.2.7", "0.2.8")

    assert "0.2.7" in result
    assert "0.2.8" in result


def test_format_version_warning_includes_upgrade_command() -> None:
    """Test that format_version_warning includes upgrade command."""
    result = format_version_warning("0.2.7", "0.2.8")

    assert "uv tool upgrade erk" in result


def test_format_version_warning_includes_must_update_message() -> None:
    """Test that format_version_warning includes urgency message."""
    result = format_version_warning("0.2.7", "0.2.8")

    assert "must update" in result


def test_format_version_warning_includes_warning_emoji() -> None:
    """Test that format_version_warning includes warning indicator."""
    result = format_version_warning("0.2.7", "0.2.8")

    assert "⚠️" in result

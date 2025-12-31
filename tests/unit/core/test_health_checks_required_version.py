"""Tests for check_required_tool_version health check.

These tests verify the health check correctly reports required version status.
Uses tmp_path to test with real filesystem I/O since the check reads version files.
"""

from pathlib import Path
from unittest.mock import patch

from erk.core.health_checks import check_required_tool_version


def test_check_fails_when_file_missing(tmp_path: Path) -> None:
    """Test that check fails when required version file doesn't exist."""
    result = check_required_tool_version(tmp_path)

    assert result.passed is False
    assert result.name == "required-version"
    assert "missing" in result.message.lower()


def test_check_fails_on_mismatch(tmp_path: Path) -> None:
    """Test that check fails when installed version doesn't match required."""
    # Create the version file with a different version
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text("99.99.99", encoding="utf-8")

    # Mock the installed version to be different
    with patch(
        "erk.core.health_checks._get_installed_erk_version",
        return_value="0.2.8",
    ):
        result = check_required_tool_version(tmp_path)

    assert result.passed is False
    assert result.name == "required-version"
    assert "mismatch" in result.message.lower()
    assert "99.99.99" in result.message
    assert "0.2.8" in result.message


def test_check_passes_when_match(tmp_path: Path) -> None:
    """Test that check passes when installed version matches required."""
    # Create the version file
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text("0.2.8", encoding="utf-8")

    # Mock the installed version to match
    with patch(
        "erk.core.health_checks._get_installed_erk_version",
        return_value="0.2.8",
    ):
        result = check_required_tool_version(tmp_path)

    assert result.passed is True
    assert result.name == "required-version"
    assert "matches" in result.message.lower()


def test_check_fails_when_installed_version_unknown(tmp_path: Path) -> None:
    """Test that check fails when installed version can't be determined."""
    # Create the version file
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text("0.2.8", encoding="utf-8")

    # Mock the installed version to be None (not installed)
    with patch(
        "erk.core.health_checks._get_installed_erk_version",
        return_value=None,
    ):
        result = check_required_tool_version(tmp_path)

    assert result.passed is False
    assert result.name == "required-version"
    assert "could not determine" in result.message.lower()

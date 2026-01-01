"""Tests for check_statusline_configured health check.

These tests verify the health check correctly reports statusline configuration
status from global Claude settings.
"""

import json
from pathlib import Path
from unittest import mock

from erk.core.health_checks import check_statusline_configured


def test_returns_info_when_no_settings_file(tmp_path: Path) -> None:
    """Test returns info-level result when no global settings file exists."""
    settings_path = tmp_path / ".claude" / "settings.json"

    with mock.patch(
        "erk.core.health_checks.get_global_claude_settings_path",
        return_value=settings_path,
    ):
        result = check_statusline_configured()

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is True
    assert "not configured" in result.message.lower()
    assert result.details is not None
    assert "erk init --statusline" in result.details


def test_returns_configured_when_erk_statusline_present(tmp_path: Path) -> None:
    """Test returns configured status when erk-statusline is set."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": "uvx erk-statusline",
                }
            }
        ),
        encoding="utf-8",
    )

    with mock.patch(
        "erk.core.health_checks.get_global_claude_settings_path",
        return_value=settings_path,
    ):
        result = check_statusline_configured()

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is False  # Not info - it's a success
    assert "erk-statusline configured" in result.message
    assert result.details is None


def test_returns_info_when_different_statusline(tmp_path: Path) -> None:
    """Test returns info-level result when different statusline is configured."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": "uvx other-statusline",
                }
            }
        ),
        encoding="utf-8",
    )

    with mock.patch(
        "erk.core.health_checks.get_global_claude_settings_path",
        return_value=settings_path,
    ):
        result = check_statusline_configured()

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is True
    # Shows existing statusline command
    assert "uvx other-statusline" in result.message
    assert "Different statusline configured" in result.message
    assert result.details is not None
    assert "erk init --statusline" in result.details


def test_returns_info_when_no_statusline_in_settings(tmp_path: Path) -> None:
    """Test returns info-level result when settings exist but no statusLine."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": []}}),
        encoding="utf-8",
    )

    with mock.patch(
        "erk.core.health_checks.get_global_claude_settings_path",
        return_value=settings_path,
    ):
        result = check_statusline_configured()

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is True
    assert "not configured" in result.message.lower()
    assert result.details is not None
    assert "erk init --statusline" in result.details

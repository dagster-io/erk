"""Tests for check_claude_erk_permission health check.

These tests verify the health check correctly reports Claude erk permission status.
Uses tmp_path to test with real filesystem I/O since the check reads settings.json.
"""

import json
from pathlib import Path

from erk.core.health_checks import check_claude_erk_permission


def test_check_returns_info_when_settings_not_found(tmp_path: Path) -> None:
    """Test that check returns info when no settings file exists."""
    # tmp_path is an empty directory - no .claude/settings.json
    result = check_claude_erk_permission(tmp_path)

    assert result.passed is True
    assert result.name == "claude erk permission"
    assert "no .claude/settings.json" in result.message.lower()


def test_check_returns_info_when_permission_configured(tmp_path: Path) -> None:
    """Test that check returns success when permission exists."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "permissions": {
                    "allow": ["Bash(erk:*)", "Bash(git:*)"],
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_claude_erk_permission(tmp_path)

    assert result.passed is True
    assert "configured" in result.message.lower()
    assert "Bash(erk:*)" in result.message


def test_check_returns_info_when_permission_missing(tmp_path: Path) -> None:
    """Test that check returns info with instructions when permission missing."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "permissions": {
                    "allow": ["Bash(git:*)"],
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_claude_erk_permission(tmp_path)

    assert result.passed is True  # Info level - always passes
    assert "not configured" in result.message.lower()
    assert result.details is not None
    assert "erk init" in result.details


def test_check_handles_invalid_json(tmp_path: Path) -> None:
    """Test that check handles invalid JSON gracefully."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ invalid json", encoding="utf-8")

    result = check_claude_erk_permission(tmp_path)

    # Should report invalid JSON as a failed check
    assert result.passed is False
    assert "invalid json" in result.message.lower()
    assert result.details is not None


def test_check_handles_empty_settings(tmp_path: Path) -> None:
    """Test that check handles empty settings object."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{}", encoding="utf-8")

    result = check_claude_erk_permission(tmp_path)

    assert result.passed is True
    assert "not configured" in result.message.lower()

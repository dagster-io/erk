"""Tests for health_checks module."""

import json
from pathlib import Path

from erk.core.health_checks import (
    CheckResult,
    check_claude_settings,
    check_erk_version,
)


def test_check_result_dataclass() -> None:
    """Test CheckResult dataclass creation."""
    result = CheckResult(
        name="test",
        passed=True,
        message="Test passed",
        details="Some details",
    )

    assert result.name == "test"
    assert result.passed is True
    assert result.message == "Test passed"
    assert result.details == "Some details"


def test_check_result_without_details() -> None:
    """Test CheckResult without optional details."""
    result = CheckResult(
        name="test",
        passed=False,
        message="Test failed",
    )

    assert result.name == "test"
    assert result.passed is False
    assert result.message == "Test failed"
    assert result.details is None


def test_check_erk_version() -> None:
    """Test that check_erk_version returns a valid result."""
    result = check_erk_version()

    # Should always pass if erk is installed (which it is since we're running tests)
    assert result.name == "erk"
    assert result.passed is True
    assert "erk" in result.message.lower()


def test_check_claude_settings_no_file(tmp_path: Path) -> None:
    """Test claude settings check when no settings file exists."""
    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is True
    assert "No .claude/settings.json" in result.message


def test_check_claude_settings_valid_json(tmp_path: Path) -> None:
    """Test claude settings check with valid settings file."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is True
    assert "looks valid" in result.message.lower() or "using defaults" in result.message.lower()


def test_check_claude_settings_invalid_json(tmp_path: Path) -> None:
    """Test claude settings check with invalid JSON."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text("{invalid json", encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is False
    assert "Invalid JSON" in result.message


def test_check_claude_settings_with_hooks(tmp_path: Path) -> None:
    """Test claude settings check with hook configuration."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = {
        "hooks": {
            "userPromptSubmit": [
                {
                    "command": "echo hello",
                }
            ]
        }
    }
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps(settings), encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is True

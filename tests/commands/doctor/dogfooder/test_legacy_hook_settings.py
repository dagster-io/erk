"""Tests for legacy hook settings health check (dogfooder feature)."""

import json
from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_hook_settings import (
    check_legacy_hook_settings,
)


def test_check_passes_when_no_settings_file(tmp_path: Path) -> None:
    """Test check passes when .claude/settings.json doesn't exist."""
    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is True
    assert result.name == "legacy-hook-settings"
    assert "No legacy" in result.message


def test_check_passes_when_no_hooks_section(tmp_path: Path) -> None:
    """Test check passes when settings.json has no hooks section."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({}), encoding="utf-8")

    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is True
    assert "No legacy" in result.message


def test_check_passes_with_modern_hook_command(tmp_path: Path) -> None:
    """Test check passes when hooks use modern erk-user-prompt-hook.py."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {"type": "command", "command": "uv run scripts/erk-user-prompt-hook.py"}
            ]
        }
    }
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is True
    assert "No legacy" in result.message


def test_check_fails_with_erk_kit_exec_command(tmp_path: Path) -> None:
    """Test check fails when hooks use 'erk kit exec' pattern."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {"type": "command", "command": "erk kit exec erk-kit user-prompt-submit"}
            ]
        }
    }
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is False
    assert result.name == "legacy-hook-settings"
    assert "1 legacy hook" in result.message
    assert result.details is not None
    assert "erk kit exec" in result.details
    assert "erk init" in result.details


def test_check_fails_with_uvx_erk_command(tmp_path: Path) -> None:
    """Test check fails when hooks use 'uvx erk@X.Y.Z' pattern."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "type": "command",
                    "command": "uvx erk@0.2.5 kit exec erk-kit session-id-injector-hook",
                }
            ]
        }
    }
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is False
    assert "1 legacy hook" in result.message
    assert result.details is not None
    assert "uvx" in result.details


def test_check_fails_with_nested_hook_structure(tmp_path: Path) -> None:
    """Test check detects legacy hooks in nested matcher structure."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "cwd:**/my-repo/**",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "erk kit exec erk-kit tripwires-reminder-hook",
                        }
                    ],
                }
            ]
        }
    }
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is False
    assert "1 legacy hook" in result.message


def test_check_counts_multiple_legacy_hooks(tmp_path: Path) -> None:
    """Test check counts all legacy hook commands found."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {"type": "command", "command": "erk kit exec erk-kit hook1"},
                {"type": "command", "command": "erk kit exec erk-kit hook2"},
                {"type": "command", "command": "uvx erk@0.2.0 kit exec erk-kit hook3"},
            ]
        }
    }
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    result = check_legacy_hook_settings(tmp_path)

    assert result.passed is False
    assert "3 legacy hook" in result.message

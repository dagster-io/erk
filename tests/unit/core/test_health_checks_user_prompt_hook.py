"""Tests for check_user_prompt_hook health check.

These tests verify the health check correctly reports UserPromptSubmit hook status.
Uses tmp_path to test with real filesystem I/O since the check reads settings.json.
"""

import json
from pathlib import Path

from erk.core.health_checks import check_user_prompt_hook


def test_check_fails_when_settings_not_found(tmp_path: Path) -> None:
    """Test that check fails when no settings file exists."""
    result = check_user_prompt_hook(tmp_path)

    assert result.passed is False
    assert result.name == "user prompt hook"
    assert "no .claude/settings.json" in result.message.lower()


def test_check_passes_when_hook_configured_nested(tmp_path: Path) -> None:
    """Test that check passes when hook exists with nested matcher structure."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "uv run scripts/erk-user-prompt-hook.py",
                                    "timeout": 30,
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_user_prompt_hook(tmp_path)

    assert result.passed is True
    assert "configured" in result.message.lower()


def test_check_passes_when_hook_configured_flat(tmp_path: Path) -> None:
    """Test that check passes when hook exists with flat structure."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "type": "command",
                            "command": "uv run scripts/erk-user-prompt-hook.py",
                            "timeout": 30,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_user_prompt_hook(tmp_path)

    assert result.passed is True
    assert "configured" in result.message.lower()


def test_check_fails_when_no_hooks_section(tmp_path: Path) -> None:
    """Test that check fails when hooks section is missing."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": []}}),
        encoding="utf-8",
    )

    result = check_user_prompt_hook(tmp_path)

    assert result.passed is False
    assert "no userpromptsubmit hook" in result.message.lower()


def test_check_fails_when_wrong_hook_command(tmp_path: Path) -> None:
    """Test that check fails when UserPromptSubmit has wrong command."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "type": "command",
                            "command": "some-other-hook.sh",
                            "timeout": 30,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_user_prompt_hook(tmp_path)

    assert result.passed is False
    assert "missing unified hook" in result.message.lower()
    assert result.details is not None
    assert "erk-user-prompt-hook.py" in result.details


def test_check_handles_empty_settings(tmp_path: Path) -> None:
    """Test that check handles empty settings object."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{}", encoding="utf-8")

    result = check_user_prompt_hook(tmp_path)

    assert result.passed is False
    assert "no userpromptsubmit hook" in result.message.lower()

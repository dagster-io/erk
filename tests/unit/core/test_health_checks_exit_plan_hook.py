"""Tests for check_exit_plan_hook health check.

These tests verify the health check correctly reports ExitPlanMode hook status.
Uses tmp_path to test with real filesystem I/O since the check reads settings.json.
"""

import json
from pathlib import Path

from erk.core.health_checks import check_exit_plan_hook


def test_check_fails_when_settings_not_found(tmp_path: Path) -> None:
    """Test that check fails when no settings file exists."""
    result = check_exit_plan_hook(tmp_path)

    assert result.passed is False
    assert result.name == "exit-plan-hook"
    assert "no .claude/settings.json" in result.message.lower()


def test_check_passes_when_hook_configured(tmp_path: Path) -> None:
    """Test that check passes when ExitPlanMode hook is configured."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "ExitPlanMode",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "ERK_HOOK_ID=exit-plan-mode-hook "
                                        "erk exec exit-plan-mode-hook"
                                    ),
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_exit_plan_hook(tmp_path)

    assert result.passed is True
    assert result.name == "exit-plan-hook"
    assert "configured" in result.message.lower()


def test_check_fails_when_no_hooks_section(tmp_path: Path) -> None:
    """Test that check fails when hooks section is missing."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": []}}),
        encoding="utf-8",
    )

    result = check_exit_plan_hook(tmp_path)

    assert result.passed is False
    assert result.name == "exit-plan-hook"
    assert "not configured" in result.message.lower()


def test_check_fails_when_wrong_matcher(tmp_path: Path) -> None:
    """Test that check fails when PreToolUse has wrong matcher."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "SomeOtherTool",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "ERK_HOOK_ID=exit-plan-mode-hook "
                                        "erk exec exit-plan-mode-hook"
                                    ),
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_exit_plan_hook(tmp_path)

    assert result.passed is False
    assert result.name == "exit-plan-hook"
    assert "not configured" in result.message.lower()


def test_check_fails_when_wrong_command(tmp_path: Path) -> None:
    """Test that check fails when ExitPlanMode matcher has wrong command."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "ExitPlanMode",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "some-other-hook.sh",
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_exit_plan_hook(tmp_path)

    assert result.passed is False
    assert result.name == "exit-plan-hook"
    assert "not configured" in result.message.lower()


def test_check_handles_empty_settings(tmp_path: Path) -> None:
    """Test that check handles empty settings object."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{}", encoding="utf-8")

    result = check_exit_plan_hook(tmp_path)

    assert result.passed is False
    assert result.name == "exit-plan-hook"
    assert "not configured" in result.message.lower()

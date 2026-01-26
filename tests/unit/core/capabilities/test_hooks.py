"""Tests for HooksCapability.

These tests verify the hook installation and detection behavior,
particularly the marker-based detection that enables hook updates.
"""

import json
from pathlib import Path

from erk.capabilities.hooks import HooksCapability
from erk.core.claude_settings import (
    ERK_EXIT_PLAN_HOOK_COMMAND,
    ERK_USER_PROMPT_HOOK_COMMAND,
)


def test_is_installed_returns_false_when_no_repo_root() -> None:
    """Test is_installed returns False when repo_root is None."""
    capability = HooksCapability()
    assert capability.is_installed(repo_root=None) is False


def test_is_installed_returns_false_when_settings_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when settings.json doesn't exist."""
    capability = HooksCapability()
    assert capability.is_installed(repo_root=tmp_path) is False


def test_is_installed_returns_false_when_hooks_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when hooks are not configured."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{}", encoding="utf-8")

    capability = HooksCapability()
    assert capability.is_installed(repo_root=tmp_path) is False


def test_is_installed_returns_true_when_current_hooks_present(tmp_path: Path) -> None:
    """Test is_installed returns True when current hooks are configured."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": ERK_EXIT_PLAN_HOOK_COMMAND}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    assert capability.is_installed(repo_root=tmp_path) is True


def test_is_installed_returns_false_for_old_hook_commands(tmp_path: Path) -> None:
    """Test is_installed returns False when old hook commands are present.

    This is the key behavior: hooks with ERK_HOOK_ID marker but different
    command text should be detected as NOT installed, triggering an update.
    """
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    # Old hook commands have the marker but different command text
    old_user_prompt = "ERK_HOOK_ID=user-prompt-hook erk exec old-command"
    old_exit_plan = "ERK_HOOK_ID=exit-plan-mode-hook erk exec old-exit"

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": old_user_prompt}],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": old_exit_plan}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    # Should return False because the exact command doesn't match current version
    assert capability.is_installed(repo_root=tmp_path) is False


def test_has_any_erk_hooks_returns_false_when_no_repo_root() -> None:
    """Test has_any_erk_hooks returns False when repo_root is None."""
    capability = HooksCapability()
    assert capability.has_any_erk_hooks(repo_root=None) is False


def test_has_any_erk_hooks_returns_false_when_settings_missing(tmp_path: Path) -> None:
    """Test has_any_erk_hooks returns False when settings.json doesn't exist."""
    capability = HooksCapability()
    assert capability.has_any_erk_hooks(repo_root=tmp_path) is False


def test_has_any_erk_hooks_returns_true_for_old_hooks(tmp_path: Path) -> None:
    """Test has_any_erk_hooks returns True for old hook commands.

    This uses marker-based detection to find any erk hooks, regardless of version.
    """
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    # Old hook command with marker
    old_user_prompt = "ERK_HOOK_ID=user-prompt-hook erk exec old-command"

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": old_user_prompt}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    assert capability.has_any_erk_hooks(repo_root=tmp_path) is True


def test_has_any_erk_hooks_returns_true_for_current_hooks(tmp_path: Path) -> None:
    """Test has_any_erk_hooks returns True for current hook commands."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    assert capability.has_any_erk_hooks(repo_root=tmp_path) is True


def test_has_any_erk_hooks_returns_false_for_non_erk_hooks(tmp_path: Path) -> None:
    """Test has_any_erk_hooks returns False for non-erk hooks."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": "some-other-hook"}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    assert capability.has_any_erk_hooks(repo_root=tmp_path) is False


def test_install_creates_hooks_in_empty_settings(tmp_path: Path) -> None:
    """Test install adds hooks to empty settings file."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{}", encoding="utf-8")

    capability = HooksCapability()
    result = capability.install(repo_root=tmp_path)

    assert result.success is True
    assert "Added erk hooks" in result.message

    # Verify hooks were written
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in updated_settings["hooks"]
    assert "PreToolUse" in updated_settings["hooks"]


def test_install_updates_old_hooks(tmp_path: Path) -> None:
    """Test install updates old erk hooks to current versions.

    This is the key behavior: when old hooks are present, install should
    replace them with current versions.
    """
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    # Old hook commands
    old_user_prompt = "ERK_HOOK_ID=user-prompt-hook erk exec old-command"
    old_exit_plan = "ERK_HOOK_ID=exit-plan-mode-hook erk exec old-exit"

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": old_user_prompt}],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": old_exit_plan}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    result = capability.install(repo_root=tmp_path)

    assert result.success is True
    # Should say "Updated" not "Added" since old hooks were present
    assert "Updated erk hooks" in result.message

    # Verify hooks were updated to current versions
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    user_prompt_command = updated_settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    exit_plan_command = updated_settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    assert user_prompt_command == ERK_USER_PROMPT_HOOK_COMMAND
    assert exit_plan_command == ERK_EXIT_PLAN_HOOK_COMMAND


def test_install_skips_when_already_current(tmp_path: Path) -> None:
    """Test install returns success without changes when hooks are current."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": ERK_EXIT_PLAN_HOOK_COMMAND}],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    result = capability.install(repo_root=tmp_path)

    assert result.success is True
    assert "already configured" in result.message


def test_install_preserves_user_hooks(tmp_path: Path) -> None:
    """Test install preserves user's custom hooks when updating erk hooks."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)

    # Old erk hook + user's custom hook
    old_erk_hook = "ERK_HOOK_ID=user-prompt-hook erk exec old-command"
    user_hook = "my-custom-lint-hook"

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*.py",
                    "hooks": [{"type": "command", "command": user_hook}],
                },
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": old_erk_hook}],
                },
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    capability = HooksCapability()
    result = capability.install(repo_root=tmp_path)

    assert result.success is True

    # Verify user's hook is preserved
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    user_hooks = [
        h for h in updated_settings["hooks"]["UserPromptSubmit"] if h["matcher"] == "*.py"
    ]
    assert len(user_hooks) == 1
    assert user_hooks[0]["hooks"][0]["command"] == user_hook


def test_install_fails_without_repo_root() -> None:
    """Test install returns failure when repo_root is None."""
    capability = HooksCapability()
    result = capability.install(repo_root=None)

    assert result.success is False
    assert "requires repo_root" in result.message


def test_install_fails_on_invalid_json(tmp_path: Path) -> None:
    """Test install returns failure for invalid JSON in settings."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ invalid json", encoding="utf-8")

    capability = HooksCapability()
    result = capability.install(repo_root=tmp_path)

    assert result.success is False
    assert "Invalid JSON" in result.message

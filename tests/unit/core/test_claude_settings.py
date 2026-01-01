"""Tests for claude_settings pure functions.

These are pure unit tests (Layer 3) - no I/O, no fakes, no mocks.
Testing the pure transformation functions for Claude settings manipulation.

Also includes integration tests (Layer 2) for read/write operations on disk.
"""

import json
from pathlib import Path

import pytest

from erk.core.claude_settings import (
    ERK_EXIT_PLAN_HOOK_COMMAND,
    ERK_PERMISSION,
    ERK_STATUSLINE_COMMAND,
    ERK_USER_PROMPT_HOOK_COMMAND,
    NoBackupCreated,
    add_erk_hooks,
    add_erk_permission,
    add_statusline_config,
    get_global_claude_settings_path,
    get_repo_claude_settings_path,
    has_erk_permission,
    has_exit_plan_hook,
    has_statusline_configured,
    has_user_prompt_hook,
    read_claude_settings,
    write_claude_settings,
)


def test_has_erk_permission_returns_true_when_present() -> None:
    """Test that has_erk_permission returns True when permission exists."""
    settings = {
        "permissions": {
            "allow": ["Bash(git:*)", "Bash(erk:*)", "Web Search(*)"],
        }
    }
    assert has_erk_permission(settings) is True


def test_has_erk_permission_returns_false_when_missing() -> None:
    """Test that has_erk_permission returns False when permission is absent."""
    settings = {
        "permissions": {
            "allow": ["Bash(git:*)", "Web Search(*)"],
        }
    }
    assert has_erk_permission(settings) is False


def test_has_erk_permission_returns_false_for_empty_allow() -> None:
    """Test that has_erk_permission returns False for empty allow list."""
    settings = {
        "permissions": {
            "allow": [],
        }
    }
    assert has_erk_permission(settings) is False


def test_has_erk_permission_returns_false_for_missing_permissions() -> None:
    """Test that has_erk_permission returns False when permissions key is missing."""
    settings: dict = {}
    assert has_erk_permission(settings) is False


def test_has_erk_permission_returns_false_for_missing_allow() -> None:
    """Test that has_erk_permission returns False when allow key is missing."""
    settings = {
        "permissions": {},
    }
    assert has_erk_permission(settings) is False


def test_add_erk_permission_adds_to_existing_list() -> None:
    """Test that add_erk_permission adds permission to existing allow list."""
    settings = {
        "permissions": {
            "allow": ["Bash(git:*)"],
        }
    }
    result = add_erk_permission(settings)

    assert ERK_PERMISSION in result["permissions"]["allow"]
    assert "Bash(git:*)" in result["permissions"]["allow"]
    # Original should not be modified
    assert ERK_PERMISSION not in settings["permissions"]["allow"]


def test_add_erk_permission_creates_permissions_if_missing() -> None:
    """Test that add_erk_permission creates permissions structure if missing."""
    settings: dict = {}
    result = add_erk_permission(settings)

    assert "permissions" in result
    assert "allow" in result["permissions"]
    assert ERK_PERMISSION in result["permissions"]["allow"]


def test_add_erk_permission_creates_allow_if_missing() -> None:
    """Test that add_erk_permission creates allow list if missing."""
    settings = {
        "permissions": {},
    }
    result = add_erk_permission(settings)

    assert "allow" in result["permissions"]
    assert ERK_PERMISSION in result["permissions"]["allow"]


def test_add_erk_permission_does_not_duplicate() -> None:
    """Test that add_erk_permission doesn't add permission if already present."""
    settings = {
        "permissions": {
            "allow": ["Bash(erk:*)"],
        }
    }
    result = add_erk_permission(settings)

    # Should have exactly one occurrence
    assert result["permissions"]["allow"].count(ERK_PERMISSION) == 1


def test_add_erk_permission_preserves_other_keys() -> None:
    """Test that add_erk_permission preserves other settings keys."""
    settings = {
        "permissions": {
            "allow": ["Bash(git:*)"],
            "ask": ["Write(*)"],
        },
        "statusLine": {
            "type": "command",
            "command": "echo test",
        },
        "alwaysThinkingEnabled": True,
    }
    result = add_erk_permission(settings)

    # Other keys should be preserved
    assert result["statusLine"]["type"] == "command"
    assert result["alwaysThinkingEnabled"] is True
    assert result["permissions"]["ask"] == ["Write(*)"]


def test_add_erk_permission_is_pure_function() -> None:
    """Test that add_erk_permission doesn't modify the input."""
    original = {
        "permissions": {
            "allow": ["Bash(git:*)"],
        }
    }
    # Make a copy of the original state
    original_allow = original["permissions"]["allow"].copy()

    add_erk_permission(original)

    # Original should be unchanged
    assert original["permissions"]["allow"] == original_allow
    assert ERK_PERMISSION not in original["permissions"]["allow"]


def test_erk_permission_constant_value() -> None:
    """Test that ERK_PERMISSION has the expected value."""
    assert ERK_PERMISSION == "Bash(erk:*)"


# --- Tests for standalone hook detection functions ---


def test_has_user_prompt_hook_returns_false_for_empty_settings() -> None:
    """Test has_user_prompt_hook returns False for empty settings."""
    assert has_user_prompt_hook({}) is False


def test_has_user_prompt_hook_returns_true_when_configured() -> None:
    """Test has_user_prompt_hook returns True when hook is configured."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ]
        }
    }
    assert has_user_prompt_hook(settings) is True


def test_has_user_prompt_hook_returns_false_for_different_command() -> None:
    """Test has_user_prompt_hook returns False for non-erk hook."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": "other-command"}],
                }
            ]
        }
    }
    assert has_user_prompt_hook(settings) is False


def test_has_exit_plan_hook_returns_false_for_empty_settings() -> None:
    """Test has_exit_plan_hook returns False for empty settings."""
    assert has_exit_plan_hook({}) is False


def test_has_exit_plan_hook_returns_true_when_configured() -> None:
    """Test has_exit_plan_hook returns True when hook is configured."""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": ERK_EXIT_PLAN_HOOK_COMMAND}],
                }
            ]
        }
    }
    assert has_exit_plan_hook(settings) is True


def test_has_exit_plan_hook_returns_false_for_wrong_matcher() -> None:
    """Test has_exit_plan_hook returns False when matcher is wrong."""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",  # Wrong matcher
                    "hooks": [{"type": "command", "command": ERK_EXIT_PLAN_HOOK_COMMAND}],
                }
            ]
        }
    }
    assert has_exit_plan_hook(settings) is False


# --- Integration tests using filesystem ---


def test_read_write_roundtrip_with_representative_settings(tmp_path: Path) -> None:
    """Test read/write roundtrip with a representative settings.json file.

    This integration test uses a realistic settings structure similar to what
    you'd find in an actual erk repository, including permissions, hooks, and
    various configuration keys.
    """
    # Representative settings matching real-world usage
    representative_settings = {
        "permissions": {
            "allow": [
                "Bash(git:*)",
                "Read(/tmp/*)",
                "Write(/tmp/*)",
            ],
            "deny": [],
            "ask": [],
        },
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "echo 'session started'",
                            "timeout": 5,
                        }
                    ],
                }
            ],
            "UserPromptSubmit": [
                {
                    "matcher": "*.py",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "echo 'python file'",
                            "timeout": 30,
                        }
                    ],
                }
            ],
        },
    }

    # Write to disk
    settings_path = get_repo_claude_settings_path(tmp_path)
    write_claude_settings(settings_path, representative_settings)

    # Verify file exists
    assert settings_path.exists()

    # Read back and verify
    loaded_settings = read_claude_settings(settings_path)
    assert loaded_settings is not None
    assert loaded_settings == representative_settings

    # Verify JSON formatting (pretty printed with indent=2)
    raw_content = settings_path.read_text(encoding="utf-8")
    assert "  " in raw_content  # Has indentation


def test_add_permission_to_representative_settings(tmp_path: Path) -> None:
    """Test adding erk permission to a representative settings file."""
    # Start with settings that don't have erk permission
    initial_settings = {
        "permissions": {
            "allow": ["Bash(git:*)", "Read(/tmp/*)"],
            "deny": [],
            "ask": ["Write(*)"],
        },
        "hooks": {
            "SessionStart": [{"matcher": "*", "hooks": []}],
        },
    }

    settings_path = get_repo_claude_settings_path(tmp_path)
    write_claude_settings(settings_path, initial_settings)

    # Read, modify, and write back
    settings = read_claude_settings(settings_path)
    assert settings is not None
    assert not has_erk_permission(settings)

    updated = add_erk_permission(settings)
    write_claude_settings(settings_path, updated)

    # Verify final state
    final = read_claude_settings(settings_path)
    assert final is not None
    assert has_erk_permission(final)
    # Verify other settings preserved
    assert final["permissions"]["ask"] == ["Write(*)"]
    assert "hooks" in final


def test_read_returns_none_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that read_claude_settings returns None when file doesn't exist."""
    settings_path = tmp_path / ".claude" / "settings.json"
    result = read_claude_settings(settings_path)
    assert result is None


def test_read_raises_on_invalid_json(tmp_path: Path) -> None:
    """Test that read_claude_settings raises JSONDecodeError for invalid JSON."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        read_claude_settings(settings_path)


# --- Tests for hook functions ---


def test_hook_command_constants() -> None:
    """Test that hook command constants have expected values."""
    assert ERK_USER_PROMPT_HOOK_COMMAND == (
        "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook"
    )
    assert ERK_EXIT_PLAN_HOOK_COMMAND == (
        "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"
    )


def test_hook_detection_returns_false_for_empty_settings() -> None:
    """Test that hook detection functions return False for empty settings."""
    settings: dict = {}
    assert has_user_prompt_hook(settings) is False
    assert has_exit_plan_hook(settings) is False


def test_hook_detection_returns_false_for_missing_hooks_key() -> None:
    """Test that hook detection returns False when hooks key is missing."""
    settings = {"permissions": {"allow": []}}
    assert has_user_prompt_hook(settings) is False
    assert has_exit_plan_hook(settings) is False


def test_hook_detection_returns_false_for_empty_hooks() -> None:
    """Test that hook detection returns False for empty hooks structure."""
    settings = {"hooks": {}}
    assert has_user_prompt_hook(settings) is False
    assert has_exit_plan_hook(settings) is False


def test_hook_detection_detects_user_prompt_hook() -> None:
    """Test that has_user_prompt_hook detects UserPromptSubmit hook."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": ERK_USER_PROMPT_HOOK_COMMAND,
                        }
                    ],
                }
            ]
        }
    }
    assert has_user_prompt_hook(settings) is True
    assert has_exit_plan_hook(settings) is False


def test_hook_detection_detects_pre_tool_use_hook() -> None:
    """Test that has_exit_plan_hook detects PreToolUse hook with ExitPlanMode matcher."""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [
                        {
                            "type": "command",
                            "command": ERK_EXIT_PLAN_HOOK_COMMAND,
                        }
                    ],
                }
            ]
        }
    }
    assert has_user_prompt_hook(settings) is False
    assert has_exit_plan_hook(settings) is True


def test_hook_detection_detects_both_hooks() -> None:
    """Test that hook detection finds both hooks when present."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": ERK_USER_PROMPT_HOOK_COMMAND,
                        }
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [
                        {
                            "type": "command",
                            "command": ERK_EXIT_PLAN_HOOK_COMMAND,
                        }
                    ],
                }
            ],
        }
    }
    assert has_user_prompt_hook(settings) is True
    assert has_exit_plan_hook(settings) is True


def test_hook_detection_ignores_wrong_matcher_for_pretooluse() -> None:
    """Test that has_exit_plan_hook only matches PreToolUse with ExitPlanMode matcher."""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",  # Wrong matcher
                    "hooks": [
                        {
                            "type": "command",
                            "command": ERK_EXIT_PLAN_HOOK_COMMAND,
                        }
                    ],
                }
            ]
        }
    }
    assert has_user_prompt_hook(settings) is False
    assert has_exit_plan_hook(settings) is False


def test_hook_detection_requires_exact_command_match() -> None:
    """Test that hook detection requires exact command string match."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "different-command",  # Different command
                        }
                    ],
                }
            ]
        }
    }
    assert has_user_prompt_hook(settings) is False
    assert has_exit_plan_hook(settings) is False


def test_hook_detection_finds_hook_among_multiple_entries() -> None:
    """Test that hook detection finds the erk hook among multiple hook entries."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*.py",
                    "hooks": [{"type": "command", "command": "other-hook"}],
                },
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "another-hook"},
                        {"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND},
                    ],
                },
            ]
        }
    }
    assert has_user_prompt_hook(settings) is True
    assert has_exit_plan_hook(settings) is False


def test_add_erk_hooks_adds_both_hooks_to_empty_settings() -> None:
    """Test that add_erk_hooks adds both hooks to empty settings."""
    settings: dict = {}
    result = add_erk_hooks(settings)

    assert "hooks" in result
    assert "UserPromptSubmit" in result["hooks"]
    assert "PreToolUse" in result["hooks"]

    # Verify UserPromptSubmit hook structure
    user_prompt_hooks = result["hooks"]["UserPromptSubmit"]
    assert len(user_prompt_hooks) == 1
    assert user_prompt_hooks[0]["matcher"] == ""
    assert user_prompt_hooks[0]["hooks"][0]["command"] == ERK_USER_PROMPT_HOOK_COMMAND

    # Verify PreToolUse hook structure
    pre_tool_hooks = result["hooks"]["PreToolUse"]
    assert len(pre_tool_hooks) == 1
    assert pre_tool_hooks[0]["matcher"] == "ExitPlanMode"
    assert pre_tool_hooks[0]["hooks"][0]["command"] == ERK_EXIT_PLAN_HOOK_COMMAND


def test_add_erk_hooks_adds_missing_user_prompt_hook() -> None:
    """Test that add_erk_hooks adds missing UserPromptSubmit hook."""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": ERK_EXIT_PLAN_HOOK_COMMAND}],
                }
            ]
        }
    }
    result = add_erk_hooks(settings)

    # PreToolUse should be unchanged
    assert len(result["hooks"]["PreToolUse"]) == 1

    # UserPromptSubmit should be added
    assert "UserPromptSubmit" in result["hooks"]
    assert len(result["hooks"]["UserPromptSubmit"]) == 1


def test_add_erk_hooks_adds_missing_pre_tool_hook() -> None:
    """Test that add_erk_hooks adds missing PreToolUse hook."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ]
        }
    }
    result = add_erk_hooks(settings)

    # UserPromptSubmit should be unchanged
    assert len(result["hooks"]["UserPromptSubmit"]) == 1

    # PreToolUse should be added
    assert "PreToolUse" in result["hooks"]
    assert len(result["hooks"]["PreToolUse"]) == 1


def test_add_erk_hooks_preserves_existing_hooks() -> None:
    """Test that add_erk_hooks preserves existing hooks when adding erk hooks."""
    settings = {
        "hooks": {
            "SessionStart": [
                {"matcher": "*", "hooks": [{"type": "command", "command": "echo start"}]}
            ],
            "UserPromptSubmit": [
                {"matcher": "*.py", "hooks": [{"type": "command", "command": "lint"}]}
            ],
        }
    }
    result = add_erk_hooks(settings)

    # SessionStart should be preserved
    assert "SessionStart" in result["hooks"]
    assert len(result["hooks"]["SessionStart"]) == 1

    # UserPromptSubmit should have the existing hook plus the erk hook
    assert len(result["hooks"]["UserPromptSubmit"]) == 2

    # PreToolUse should be added
    assert "PreToolUse" in result["hooks"]


def test_add_erk_hooks_does_not_duplicate_hooks() -> None:
    """Test that add_erk_hooks doesn't add hooks if already present."""
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
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
    result = add_erk_hooks(settings)

    # Should not have duplicates
    assert len(result["hooks"]["UserPromptSubmit"]) == 1
    assert len(result["hooks"]["PreToolUse"]) == 1


def test_add_erk_hooks_is_pure_function() -> None:
    """Test that add_erk_hooks doesn't modify the input."""
    original = {"hooks": {"SessionStart": []}}
    original_copy = json.loads(json.dumps(original))

    add_erk_hooks(original)

    # Original should be unchanged
    assert original == original_copy


def test_add_erk_hooks_preserves_other_settings() -> None:
    """Test that add_erk_hooks preserves other top-level settings."""
    settings = {
        "permissions": {"allow": ["Bash(git:*)"]},
        "statusLine": {"type": "command", "command": "echo status"},
        "alwaysThinkingEnabled": True,
    }
    result = add_erk_hooks(settings)

    # Other settings should be preserved
    assert result["permissions"]["allow"] == ["Bash(git:*)"]
    assert result["statusLine"]["type"] == "command"
    assert result["alwaysThinkingEnabled"] is True


# --- Tests for backup file creation ---


def test_write_claude_settings_creates_backup(tmp_path: Path) -> None:
    """Test that write_claude_settings creates backup of existing file."""
    settings_path = get_repo_claude_settings_path(tmp_path)

    # Create initial settings
    initial_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
    write_claude_settings(settings_path, initial_settings)

    # Write new settings (should create backup)
    new_settings = {"permissions": {"allow": ["Bash(erk:*)"]}}
    write_claude_settings(settings_path, new_settings)

    # Verify backup exists and contains original content
    backup_path = settings_path.with_suffix(".json.bak")
    assert backup_path.exists()
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content == initial_settings

    # Verify new settings were written
    current_content = json.loads(settings_path.read_text(encoding="utf-8"))
    assert current_content == new_settings


def test_write_claude_settings_no_backup_for_new_file(tmp_path: Path) -> None:
    """Test that write_claude_settings doesn't create backup for new file."""
    settings_path = get_repo_claude_settings_path(tmp_path)

    # Write to non-existent file
    settings = {"permissions": {"allow": ["Bash(erk:*)"]}}
    write_claude_settings(settings_path, settings)

    # Verify no backup was created
    backup_path = settings_path.with_suffix(".json.bak")
    assert not backup_path.exists()


def test_write_claude_settings_returns_backup_path(tmp_path: Path) -> None:
    """Test that write_claude_settings returns the backup path when backup is created."""
    settings_path = get_repo_claude_settings_path(tmp_path)

    # Create initial settings
    initial_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
    write_claude_settings(settings_path, initial_settings)

    # Write new settings - should return backup path
    new_settings = {"permissions": {"allow": ["Bash(erk:*)"]}}
    result = write_claude_settings(settings_path, new_settings)

    # Verify return value is the backup path
    assert isinstance(result, Path)
    assert result == settings_path.with_suffix(".json.bak")
    assert result.exists()


def test_write_claude_settings_returns_no_backup_sentinel(tmp_path: Path) -> None:
    """Test that write_claude_settings returns NoBackupCreated for new file."""
    settings_path = get_repo_claude_settings_path(tmp_path)

    # Write to non-existent file - should return sentinel
    settings = {"permissions": {"allow": ["Bash(erk:*)"]}}
    result = write_claude_settings(settings_path, settings)

    # Verify return value is the sentinel
    assert isinstance(result, NoBackupCreated)


# --- Tests for status line functions ---


def test_erk_statusline_command_constant() -> None:
    """Test that ERK_STATUSLINE_COMMAND has the expected value."""
    assert ERK_STATUSLINE_COMMAND == "erk-statusline"


def test_get_global_claude_settings_path() -> None:
    """Test that get_global_claude_settings_path returns expected path."""
    path = get_global_claude_settings_path()
    assert path == Path.home() / ".claude" / "settings.json"


def test_has_statusline_configured_returns_true_when_present() -> None:
    """Test that has_statusline_configured returns True when statusLine exists."""
    settings = {
        "statusLine": {
            "type": "command",
            "command": "erk-statusline",
        }
    }
    assert has_statusline_configured(settings) is True


def test_has_statusline_configured_returns_false_when_missing() -> None:
    """Test that has_statusline_configured returns False when statusLine is missing."""
    settings: dict = {}
    assert has_statusline_configured(settings) is False


def test_has_statusline_configured_returns_true_for_any_statusline() -> None:
    """Test that has_statusline_configured returns True for any statusLine config."""
    settings = {
        "statusLine": {
            "type": "static",
            "text": "My custom status",
        }
    }
    assert has_statusline_configured(settings) is True


def test_add_statusline_config_adds_to_empty_settings() -> None:
    """Test that add_statusline_config adds statusLine to empty settings."""
    settings: dict = {}
    result = add_statusline_config(settings)

    assert "statusLine" in result
    assert result["statusLine"]["type"] == "command"
    assert result["statusLine"]["command"] == ERK_STATUSLINE_COMMAND
    # Original should not be modified
    assert "statusLine" not in settings


def test_add_statusline_config_overwrites_existing() -> None:
    """Test that add_statusline_config overwrites existing statusLine."""
    settings = {
        "statusLine": {
            "type": "static",
            "text": "Old status",
        }
    }
    result = add_statusline_config(settings)

    assert result["statusLine"]["type"] == "command"
    assert result["statusLine"]["command"] == ERK_STATUSLINE_COMMAND
    # Original should not be modified
    assert settings["statusLine"]["type"] == "static"


def test_add_statusline_config_preserves_other_settings() -> None:
    """Test that add_statusline_config preserves other settings keys."""
    settings = {
        "permissions": {"allow": ["Bash(git:*)"]},
        "hooks": {"SessionStart": []},
        "alwaysThinkingEnabled": True,
    }
    result = add_statusline_config(settings)

    assert result["permissions"]["allow"] == ["Bash(git:*)"]
    assert result["hooks"]["SessionStart"] == []
    assert result["alwaysThinkingEnabled"] is True
    assert result["statusLine"]["type"] == "command"


def test_add_statusline_config_is_pure_function() -> None:
    """Test that add_statusline_config doesn't modify the input."""
    original = {"permissions": {"allow": []}}
    original_copy = json.loads(json.dumps(original))

    add_statusline_config(original)

    # Original should be unchanged
    assert original == original_copy
    assert "statusLine" not in original

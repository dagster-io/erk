"""Tests for claude_settings pure functions.

These are pure unit tests (Layer 3) - no I/O, no fakes, no mocks.
Testing the pure transformation functions for Claude settings manipulation.

Also includes integration tests (Layer 2) for read/write operations on disk.
"""

import json
from pathlib import Path

import pytest

from erk.core.claude_settings import (
    ERK_PERMISSION,
    add_erk_permission,
    get_repo_claude_settings_path,
    has_erk_permission,
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

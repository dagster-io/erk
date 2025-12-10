"""Tests for claude_settings pure functions.

These are pure unit tests (Layer 3) - no I/O, no fakes, no mocks.
Testing the pure transformation functions for Claude settings manipulation.
"""

from erk.core.claude_settings import (
    ERK_PERMISSION,
    add_erk_permission,
    has_erk_permission,
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

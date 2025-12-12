"""Tests for hooks data models."""

import pytest
from pydantic import ValidationError

from erk.kits.hooks.models import (
    ClaudeSettings,
    HookDefinition,
    HookEntry,
    MatcherGroup,
)


class TestHookEntry:
    """Tests for HookEntry model."""

    def test_create_valid_entry(self) -> None:
        """Test creating valid hook entry."""
        cmd = 'ERK_KIT_ID=test-kit ERK_HOOK_ID=test-hook python3 "/path/to/script.py"'
        entry = HookEntry(command=cmd, timeout=30)
        assert entry.command == cmd
        assert entry.timeout == 30

    def test_immutability(self) -> None:
        """Test that entry is immutable."""
        entry = HookEntry(command="python3 script.py", timeout=30)
        with pytest.raises((AttributeError, ValidationError)):
            entry.command = "new command"  # type: ignore

    def test_rejects_negative_timeout(self) -> None:
        """Test that negative timeout is rejected."""
        with pytest.raises(ValidationError):
            HookEntry(command="python3 script.py", timeout=-1)

    def test_rejects_zero_timeout(self) -> None:
        """Test that zero timeout is rejected."""
        with pytest.raises(ValidationError):
            HookEntry(command="python3 script.py", timeout=0)


class TestMatcherGroup:
    """Tests for MatcherGroup model."""

    def test_create_valid_group(self) -> None:
        """Test creating valid matcher group."""
        cmd = "ERK_KIT_ID=test-kit ERK_HOOK_ID=test-hook python3 script.py"
        entry = HookEntry(command=cmd, timeout=30)
        group = MatcherGroup(matcher="**", hooks=[entry])
        assert group.matcher == "**"
        assert len(group.hooks) == 1

    def test_empty_hooks_list(self) -> None:
        """Test group with empty hooks list."""
        group = MatcherGroup(matcher="**", hooks=[])
        assert group.matcher == "**"
        assert len(group.hooks) == 0

    def test_immutability(self) -> None:
        """Test that group is immutable."""
        group = MatcherGroup(matcher="**", hooks=[])
        with pytest.raises((AttributeError, ValidationError)):
            group.matcher = "*.py"  # type: ignore


class TestClaudeSettings:
    """Tests for ClaudeSettings model."""

    def test_create_empty_settings(self) -> None:
        """Test creating empty settings."""
        settings = ClaudeSettings()
        assert settings.permissions is None
        assert settings.hooks is None

    def test_create_with_hooks(self) -> None:
        """Test creating settings with hooks."""
        cmd = "ERK_KIT_ID=test-kit ERK_HOOK_ID=test-hook python3 script.py"
        entry = HookEntry(command=cmd, timeout=30)
        group = MatcherGroup(matcher="**", hooks=[entry])
        settings = ClaudeSettings(hooks={"UserPromptSubmit": [group]})
        assert settings.hooks is not None
        assert "UserPromptSubmit" in settings.hooks

    def test_preserves_unknown_fields(self) -> None:
        """Test that unknown fields are preserved."""
        data = {
            "permissions": {"allow": ["git:*"]},
            "hooks": {},
            "unknown_field": "value",
            "another_field": 123,
        }
        settings = ClaudeSettings.model_validate(data)
        assert settings.model_extra is not None
        assert "unknown_field" in settings.model_extra
        assert settings.model_extra["unknown_field"] == "value"
        assert settings.model_extra["another_field"] == 123


class TestHookDefinition:
    """Tests for HookDefinition model."""

    def test_create_valid_definition(self) -> None:
        """Test creating valid hook definition."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher="**",
            invocation="dot-agent run test-kit test-hook",
            description="Test hook",
            timeout=30,
        )
        assert hook.id == "test-hook"
        assert hook.lifecycle == "UserPromptSubmit"
        assert hook.timeout == 30

    def test_default_timeout(self) -> None:
        """Test default timeout value."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher="**",
            invocation="dot-agent run test-kit test-hook",
            description="Test hook",
        )
        assert hook.timeout == 30

    def test_immutability(self) -> None:
        """Test that definition is immutable."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher="**",
            invocation="dot-agent run test-kit test-hook",
            description="Test hook",
        )
        with pytest.raises((AttributeError, ValidationError)):
            hook.id = "new-id"  # type: ignore

    def test_rejects_whitespace_only_lifecycle(self) -> None:
        """Test that whitespace-only lifecycle is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="   ",
                matcher="**",
                invocation="dot-agent run test-kit test-hook",
                description="Test hook",
            )

    def test_optional_matcher(self) -> None:
        """Test that matcher can be omitted."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            invocation="dot-agent run test-kit test-hook",
            description="Test hook",
        )
        assert hook.matcher is None

    def test_explicit_none_matcher(self) -> None:
        """Test that matcher can be explicitly set to None."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher=None,
            invocation="dot-agent run test-kit test-hook",
            description="Test hook",
        )
        assert hook.matcher is None

    def test_rejects_whitespace_only_invocation(self) -> None:
        """Test that whitespace-only invocation is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                invocation="   ",
                description="Test hook",
            )

    def test_rejects_whitespace_only_description(self) -> None:
        """Test that whitespace-only description is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                invocation="dot-agent run test-kit test-hook",
                description="   ",
            )

    def test_rejects_negative_timeout(self) -> None:
        """Test that negative timeout is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                invocation="dot-agent run test-kit test-hook",
                description="Test hook",
                timeout=-1,
            )

    def test_rejects_zero_timeout(self) -> None:
        """Test that zero timeout is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                invocation="dot-agent run test-kit test-hook",
                description="Test hook",
                timeout=0,
            )

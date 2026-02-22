"""Tests for InteractiveAgentConfig dataclass and permission mode mapping."""

import pytest

from erk_shared.context.types import InteractiveAgentConfig, permission_mode_to_claude


def test_default_values() -> None:
    """InteractiveAgentConfig.default() returns expected defaults."""
    config = InteractiveAgentConfig.default()

    assert config.backend == "claude"
    assert config.model is None
    assert config.verbose is False
    assert config.permission_mode == "edits"
    assert config.dangerous is False
    assert config.allow_dangerous is False


def test_with_overrides_all_none_returns_original() -> None:
    """with_overrides() with all None returns equivalent config."""
    config = InteractiveAgentConfig(
        backend="claude",
        model="opus",
        verbose=True,
        permission_mode="plan",
        dangerous=True,
        allow_dangerous=True,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=None,
    )

    assert result.backend == "claude"
    assert result.model == "opus"
    assert result.verbose is True  # verbose is preserved (not overridable)
    assert result.permission_mode == "plan"
    assert result.dangerous is True
    assert result.allow_dangerous is True


def test_with_overrides_permission_mode() -> None:
    """with_overrides() can override permission_mode."""
    config = InteractiveAgentConfig.default()

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=None,
    )

    assert result.permission_mode == "plan"
    # Other values remain unchanged
    assert result.model is None
    assert result.dangerous is False
    assert result.allow_dangerous is False


def test_with_overrides_model() -> None:
    """with_overrides() can override model."""
    config = InteractiveAgentConfig(
        backend="claude",
        model="haiku",
        verbose=False,
        permission_mode="edits",
        dangerous=False,
        allow_dangerous=False,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override="opus",
        dangerous_override=None,
        allow_dangerous_override=None,
    )

    assert result.model == "opus"
    # Original model was "haiku", now overridden


def test_with_overrides_dangerous() -> None:
    """with_overrides() can override dangerous."""
    config = InteractiveAgentConfig(
        backend="claude",
        model=None,
        verbose=False,
        permission_mode="edits",
        dangerous=False,
        allow_dangerous=False,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override=None,
        dangerous_override=True,
        allow_dangerous_override=None,
    )

    assert result.dangerous is True
    assert result.allow_dangerous is False


def test_with_overrides_allow_dangerous() -> None:
    """with_overrides() can override allow_dangerous."""
    config = InteractiveAgentConfig(
        backend="claude",
        model=None,
        verbose=False,
        permission_mode="edits",
        dangerous=False,
        allow_dangerous=False,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=True,
    )

    assert result.dangerous is False
    assert result.allow_dangerous is True


def test_with_overrides_multiple() -> None:
    """with_overrides() can override multiple values at once."""
    config = InteractiveAgentConfig.default()

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override="opus",
        dangerous_override=True,
        allow_dangerous_override=True,
    )

    assert result.permission_mode == "plan"
    assert result.model == "opus"
    assert result.dangerous is True
    assert result.allow_dangerous is True
    assert result.verbose is False  # Not overridable via this method


def test_permission_mode_to_claude_safe() -> None:
    """permission_mode_to_claude maps 'safe' to 'default'."""
    assert permission_mode_to_claude("safe") == "default"


def test_permission_mode_to_claude_edits() -> None:
    """permission_mode_to_claude maps 'edits' to 'acceptEdits'."""
    assert permission_mode_to_claude("edits") == "acceptEdits"


def test_permission_mode_to_claude_plan() -> None:
    """permission_mode_to_claude maps 'plan' to 'plan'."""
    assert permission_mode_to_claude("plan") == "plan"


def test_permission_mode_to_claude_dangerous() -> None:
    """permission_mode_to_claude maps 'dangerous' to 'bypassPermissions'."""
    assert permission_mode_to_claude("dangerous") == "bypassPermissions"


def test_permission_mode_to_claude_unknown_raises() -> None:
    """permission_mode_to_claude raises ValueError for unknown mode."""
    with pytest.raises(ValueError, match="Unknown permission_mode"):
        permission_mode_to_claude("invalid")  # type: ignore[arg-type]


def test_with_overrides_preserves_codex_backend() -> None:
    """with_overrides() preserves backend='codex' through override calls."""
    config = InteractiveAgentConfig(
        backend="codex",
        model=None,
        verbose=False,
        permission_mode="edits",
        dangerous=False,
        allow_dangerous=False,
    )

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override="gpt-4",
        dangerous_override=None,
        allow_dangerous_override=True,
    )

    # Backend is preserved through the override chain
    assert result.backend == "codex"
    # Other overrides applied correctly
    assert result.permission_mode == "plan"
    assert result.model == "gpt-4"
    assert result.allow_dangerous is True


def test_with_overrides_returns_new_instance() -> None:
    """with_overrides() returns a new instance, not mutating original."""
    config = InteractiveAgentConfig.default()

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override="opus",
        dangerous_override=True,
        allow_dangerous_override=True,
    )

    # Original is unchanged
    assert config.permission_mode == "edits"
    assert config.model is None
    assert config.dangerous is False
    assert config.allow_dangerous is False

    # Result has new values
    assert result.permission_mode == "plan"
    assert result.model == "opus"
    assert result.dangerous is True
    assert result.allow_dangerous is True

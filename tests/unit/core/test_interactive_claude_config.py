"""Tests for InteractiveClaudeConfig dataclass."""

from erk_shared.context.types import InteractiveClaudeConfig


def test_default_values() -> None:
    """InteractiveClaudeConfig.default() returns expected defaults."""
    config = InteractiveClaudeConfig.default()

    assert config.model is None
    assert config.verbose is False
    assert config.permission_mode == "acceptEdits"
    assert config.dangerous is False


def test_with_overrides_all_none_returns_original() -> None:
    """with_overrides() with all None returns equivalent config."""
    config = InteractiveClaudeConfig(
        model="opus",
        verbose=True,
        permission_mode="plan",
        dangerous=True,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override=None,
        dangerous_override=None,
    )

    assert result.model == "opus"
    assert result.verbose is True  # verbose is preserved (not overridable)
    assert result.permission_mode == "plan"
    assert result.dangerous is True


def test_with_overrides_permission_mode() -> None:
    """with_overrides() can override permission_mode."""
    config = InteractiveClaudeConfig.default()

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
    )

    assert result.permission_mode == "plan"
    # Other values remain unchanged
    assert result.model is None
    assert result.dangerous is False


def test_with_overrides_model() -> None:
    """with_overrides() can override model."""
    config = InteractiveClaudeConfig(
        model="haiku",
        verbose=False,
        permission_mode="acceptEdits",
        dangerous=False,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override="opus",
        dangerous_override=None,
    )

    assert result.model == "opus"
    # Original model was "haiku", now overridden


def test_with_overrides_dangerous() -> None:
    """with_overrides() can override dangerous."""
    config = InteractiveClaudeConfig(
        model=None,
        verbose=False,
        permission_mode="acceptEdits",
        dangerous=False,
    )

    result = config.with_overrides(
        permission_mode_override=None,
        model_override=None,
        dangerous_override=True,
    )

    assert result.dangerous is True


def test_with_overrides_multiple() -> None:
    """with_overrides() can override multiple values at once."""
    config = InteractiveClaudeConfig.default()

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override="opus",
        dangerous_override=True,
    )

    assert result.permission_mode == "plan"
    assert result.model == "opus"
    assert result.dangerous is True
    assert result.verbose is False  # Not overridable via this method


def test_with_overrides_returns_new_instance() -> None:
    """with_overrides() returns a new instance, not mutating original."""
    config = InteractiveClaudeConfig.default()

    result = config.with_overrides(
        permission_mode_override="plan",
        model_override="opus",
        dangerous_override=True,
    )

    # Original is unchanged
    assert config.permission_mode == "acceptEdits"
    assert config.model is None
    assert config.dangerous is False

    # Result has new values
    assert result.permission_mode == "plan"
    assert result.model == "opus"
    assert result.dangerous is True

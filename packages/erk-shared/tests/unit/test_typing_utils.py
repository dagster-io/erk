"""Tests for typing utilities."""

from typing import Literal

from erk_shared.core.typing_utils import narrow_to_literal

StatusType = Literal["open", "closed", "pending"]


def test_narrow_to_literal_valid_value() -> None:
    """Test narrowing a valid string to Literal type."""
    result = narrow_to_literal("open", StatusType)
    assert result == "open"


def test_narrow_to_literal_another_valid_value() -> None:
    """Test narrowing another valid string value."""
    result = narrow_to_literal("closed", StatusType)
    assert result == "closed"


def test_narrow_to_literal_invalid_value() -> None:
    """Test narrowing an invalid string returns None."""
    result = narrow_to_literal("invalid", StatusType)
    assert result is None


def test_narrow_to_literal_none_input() -> None:
    """Test narrowing None returns None."""
    result = narrow_to_literal(None, StatusType)
    assert result is None


def test_narrow_to_literal_empty_string() -> None:
    """Test narrowing empty string returns None (not a valid value)."""
    result = narrow_to_literal("", StatusType)
    assert result is None


def test_narrow_to_literal_case_sensitive() -> None:
    """Test that narrowing is case-sensitive."""
    result = narrow_to_literal("OPEN", StatusType)
    assert result is None


def test_narrow_to_literal_preserves_type() -> None:
    """Test that the returned value has the correct type for type checkers."""
    # This test validates that the function signature works correctly
    # with type checkers - if this code compiles/runs, it passes
    result: StatusType | None = narrow_to_literal("pending", StatusType)
    assert result == "pending"

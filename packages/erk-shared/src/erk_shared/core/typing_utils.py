"""Typing utilities for type narrowing and validation.

This module provides utilities for safely narrowing types at runtime,
particularly for Literal types that need validation against a set of
valid string values.
"""

from typing import Any, TypeVar, cast, get_args

# TypeVar bound to str for Literal string types
LiteralT = TypeVar("LiteralT", bound=str)


def narrow_to_literal(
    value: str | None,
    literal_type: Any,
) -> LiteralT | None:
    """Narrow a string value to a Literal type if valid.

    Uses get_args() to extract valid values from a Literal type alias and
    validates the input string against them. Returns the narrowed type
    if valid, None otherwise.

    This implements LBYL (Look Before You Leap) pattern for Literal
    type validation without raising exceptions.

    Args:
        value: String value to narrow, or None
        literal_type: The Literal type alias to narrow to (e.g., LearnStatusValue).
            This should be a type alias like `Literal["a", "b"]`, not a `type`.

    Returns:
        The value cast to the Literal type if valid, None otherwise

    Examples:
        >>> from typing import Literal
        >>> StatusType = Literal["open", "closed"]
        >>> narrow_to_literal("open", StatusType)
        'open'
        >>> narrow_to_literal("invalid", StatusType)
        None
        >>> narrow_to_literal(None, StatusType)
        None
    """
    if value is None:
        return None

    valid_values = get_args(literal_type)
    if value in valid_values:
        return cast(LiteralT, value)

    return None

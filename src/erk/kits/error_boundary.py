"""Error boundary handling for CLI commands.

This module provides decorators to catch well-known exceptions at CLI entry points
and display clean error messages without stack traces.
"""

import functools
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

from erk.kits.sources.exceptions import DotAgentNonIdealStateException

T = TypeVar("T", bound=Callable[..., Any])


def cli_error_boundary(func: T) -> T:
    """Decorator that catches all exceptions and displays appropriate error messages.

    This decorator should be applied to CLI command entry points to provide
    user-friendly error messages. It distinguishes between:
    - DotAgentNonIdealStateException and subclasses: Shows clean error messages
    - Unexpected exceptions: Always shows full stack traces for debugging

    The debug flag is still available in the Click context for potential future use.

    Example:
        @click.command()
        @cli_error_boundary
        def my_command():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from erk.kits.cli.output import user_output

        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if this is a custom DotAgentNonIdealStateException
            if isinstance(e, DotAgentNonIdealStateException):
                # Custom exceptions get clean error messages
                user_output(f"Error: {e}")
            else:
                # Unexpected exceptions always show full stack trace
                user_output(traceback.format_exc())

            raise SystemExit(1) from None

    return wrapper  # type: ignore[return-value]

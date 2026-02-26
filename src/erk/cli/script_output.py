"""Output utilities for exec scripts.

Exec scripts communicate results via JSON to stdout. This module provides
consistent error handling that outputs structured JSON rather than raising
exceptions, supporting shell scripting patterns.
"""

import functools
import json
from collections.abc import Callable
from typing import Any, NoReturn

import click

from erk_shared.non_ideal_state import NonIdealStateError


def handle_non_ideal_exit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Click command decorator: catches NonIdealStateError and exits with JSON error."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except NonIdealStateError as e:
            exit_with_error(e.error_type, str(e))

    return wrapper


def exit_with_error(error_type: str, message: str) -> NoReturn:
    """Output JSON error and exit with code 0.

    Exec commands exit with 0 even on error to support || true patterns
    in shell scripts. The error is communicated via JSON output.

    Args:
        error_type: Machine-readable error category (e.g., "no_pr_for_branch")
        message: Human-readable error message

    Raises:
        SystemExit: Always exits with code 0 after printing JSON
    """
    error_json = json.dumps(
        {"success": False, "error_type": error_type, "message": message},
        indent=2,
    )
    click.echo(error_json)
    raise SystemExit(0)

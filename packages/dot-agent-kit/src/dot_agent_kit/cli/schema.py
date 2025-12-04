"""Schema-based CLI command support for kit commands.

This module provides decorators and utilities for creating CLI commands that:
1. Automatically pass Click context to command functions
2. Generate JSON schema documentation in --help output
3. Handle JSON serialization of dataclass results
4. Control exit codes based on result types
"""

import dataclasses
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

import click


class SchemaCommand(click.Command):
    """Click Command that displays schema documentation in help text.

    The schema documentation is passed via the epilog parameter and will be
    displayed at the bottom of the --help output.
    """

    pass


def build_epilog(*result_types: type) -> str:
    """Build help text epilog documenting result schemas.

    Args:
        *result_types: Dataclass types that the command can return

    Returns:
        Formatted epilog text showing JSON schemas for each result type
    """
    if not result_types:
        return ""

    lines = ["\nResult Schemas:\n"]

    for result_type in result_types:
        if not dataclasses.is_dataclass(result_type):
            continue

        lines.append(f"  {result_type.__name__}:")

        # Get field info
        fields = dataclasses.fields(result_type)
        for field in fields:
            # Format type annotation
            type_str = str(field.type).replace("typing.", "")
            lines.append(f"    {field.name}: {type_str}")

        lines.append("")

    return "\n".join(lines)


def kit_json_command(
    name: str,
    results: list[type],
    error_type: type | None = None,
    exit_on_error: bool = True,
    **click_kwargs: Any,
) -> Callable[[Callable[..., object]], click.Command]:
    """Decorator for kit CLI commands that output JSON.

    Automatically:
    - Passes Click context as first argument to the wrapped function
    - Generates JSON schema documentation for --help
    - Handles JSON serialization of dataclass results
    - Sets exit code based on exit_on_error parameter

    Args:
        name: Command name
        results: List of dataclass types this command can return
        error_type: Type representing error results (exits 1 if exit_on_error=True)
        exit_on_error: If True, exit 1 on error_type results; if False, always exit 0
        **click_kwargs: Additional arguments passed to click.command()

    Returns:
        Decorated Click command

    Example:
        @kit_json_command(
            name="my-command",
            results=[SuccessResult, ErrorResult],
            error_type=ErrorResult,
            exit_on_error=True,
        )
        def my_command(ctx: click.Context, arg: str) -> SuccessResult | ErrorResult:
            if arg == "valid":
                return SuccessResult(message="Success!")
            return ErrorResult(error="Invalid argument")
    """

    def decorator(func: Callable[..., object]) -> click.Command:
        @wraps(func)
        def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
            # Call the wrapped function, passing ctx as first argument
            result = func(ctx, *args, **kwargs)

            # Output JSON
            if dataclasses.is_dataclass(result) and not isinstance(result, type):
                click.echo(json.dumps(dataclasses.asdict(result), indent=2))
            else:
                click.echo(json.dumps(result, indent=2))

            # Exit with error code if error result AND exit_on_error=True
            if exit_on_error and error_type and isinstance(result, error_type):
                raise SystemExit(1)

        # Build command with schema epilog AND pass_context
        cmd = click.command(
            name=name,
            cls=SchemaCommand,
            epilog=build_epilog(*results),
            **click_kwargs,
        )(click.pass_context(wrapper))

        return cmd

    return decorator

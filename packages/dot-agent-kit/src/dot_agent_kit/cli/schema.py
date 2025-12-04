"""JSON schema documentation generation from dataclasses using Pydantic.

This module provides runtime introspection of dataclasses to generate
human-readable JSON schema documentation for CLI command help text.

Example usage:
    from dataclasses import dataclass
    from typing import Literal
    from dot_agent_kit.cli.schema import kit_json_command

    @dataclass
    class SuccessResult:
        '''Success result with data.'''
        success: bool
        data: str

    @dataclass
    class ErrorResult:
        '''Error result with message.'''
        success: bool
        error: Literal["not_found", "invalid"]
        message: str

    @kit_json_command(
        name="my-command",
        results=[SuccessResult, ErrorResult],
        error_type=ErrorResult,
    )
    @click.argument("value")
    def my_command(value: str) -> SuccessResult | ErrorResult:
        '''Do something useful.'''
        return impl(value)
"""

import dataclasses
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

import click
from pydantic import TypeAdapter


def _format_json_schema_type(schema: dict[str, Any]) -> str:
    """Convert JSON Schema type info to readable string.

    Args:
        schema: JSON Schema dict from Pydantic TypeAdapter

    Returns:
        Human-readable type string
    """
    # Handle Literal types (enum in JSON Schema)
    if "enum" in schema:
        # Quote strings, leave numbers unquoted
        formatted = [f'"{v}"' if isinstance(v, str) else str(v) for v in schema["enum"]]
        return " | ".join(formatted)

    type_ = schema.get("type")
    if type_ == "boolean":
        return "boolean"
    if type_ == "integer":
        return "integer"
    if type_ == "number":
        return "number"
    if type_ == "string":
        return "string"
    if type_ == "null":
        return "null"
    if type_ == "array":
        items = schema.get("items", {})
        item_type = _format_json_schema_type(items)
        return f"list[{item_type}]"
    if type_ == "object":
        # Could be dict[K, V] - check additionalProperties
        additional = schema.get("additionalProperties")
        if additional:
            value_type = _format_json_schema_type(additional)
            return f"dict[string, {value_type}]"
        return "object"

    # Handle anyOf (unions including Optional)
    if "anyOf" in schema:
        types = [_format_json_schema_type(s) for s in schema["anyOf"]]
        return " | ".join(types)

    return "any"


def generate_schema(dc_class: type) -> str:
    """Generate schema documentation text from a dataclass using Pydantic.

    Uses Pydantic's TypeAdapter to introspect the dataclass and generate
    a human-readable schema.

    Args:
        dc_class: Dataclass type to generate schema for

    Returns:
        Formatted schema text with title and field descriptions

    Raises:
        TypeError: If dc_class is not a dataclass

    Example:
        >>> from dataclasses import dataclass
        >>> from typing import Literal
        >>> @dataclass
        ... class ParseError:
        ...     '''Error result when parsing fails.'''
        ...     success: bool
        ...     error: Literal["invalid_format", "invalid_number"]
        ...     message: str
        >>> print(generate_schema(ParseError))
        Error result when parsing fails.
          success: boolean
          error: "invalid_format" | "invalid_number"
          message: string
    """
    if not dataclasses.is_dataclass(dc_class):
        raise TypeError(f"{dc_class.__name__} is not a dataclass")

    adapter = TypeAdapter(dc_class)
    schema = adapter.json_schema()

    # Get title from docstring or class name
    doc = dc_class.__doc__
    title = doc.strip().split("\n")[0] if doc else dc_class.__name__

    lines = [title]
    for name, field_schema in schema.get("properties", {}).items():
        type_str = _format_json_schema_type(field_schema)
        lines.append(f"  {name}: {type_str}")

    return "\n".join(lines)


def build_epilog(*dataclasses: type) -> str:
    """Combine multiple dataclass schemas into Click epilog text.

    Generates a "JSON Output Schema:" section suitable for Click command
    epilog parameter.

    Args:
        *dataclasses: One or more dataclass types to document

    Returns:
        Formatted epilog text with header and schemas
    """
    schemas = [generate_schema(dc) for dc in dataclasses]
    return "JSON Output Schema:\n\n" + "\n\n".join(schemas)


class SchemaCommand(click.Command):
    """Click Command subclass that preserves newlines in epilog.

    By default, Click reformats epilog text and collapses newlines.
    This subclass preserves formatting for schema documentation.
    """

    def format_epilog(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format epilog preserving original formatting."""
        if self.epilog:
            formatter.write_paragraph()
            for line in self.epilog.splitlines():
                formatter.write_text(line)


def kit_json_command(
    name: str,
    results: list[type],
    error_type: type | None = None,
    **click_kwargs: Any,
) -> Callable[[Callable[..., object]], click.Command]:
    """Decorator for kit CLI commands that output JSON.

    Automatically:
    - Generates JSON schema documentation for --help
    - Handles JSON serialization of dataclass results
    - Sets exit code 1 for error results

    Args:
        name: CLI command name
        results: List of dataclass types that the command can return
        error_type: Optional type that indicates an error (triggers exit code 1)
        **click_kwargs: Additional arguments to pass to click.command()

    Returns:
        Decorator that creates a Click command

    Example:
        @kit_json_command(
            name="parse-issue-reference",
            results=[ParsedIssue, ParseError],
            error_type=ParseError,
        )
        @click.argument("issue_reference")
        def parse_issue_reference(issue_reference: str) -> ParsedIssue | ParseError:
            return _impl(issue_reference)
    """

    def decorator(func: Callable[..., object]) -> click.Command:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            result = func(*args, **kwargs)

            # Output JSON - check for dataclass instance (not class)
            if dataclasses.is_dataclass(result) and not isinstance(result, type):
                click.echo(json.dumps(dataclasses.asdict(result), indent=2))
            else:
                click.echo(json.dumps(result, indent=2))

            # Exit with error code if error result
            if error_type and isinstance(result, error_type):
                raise SystemExit(1)

        # Build command with schema epilog
        cmd = click.command(
            name=name,
            cls=SchemaCommand,
            epilog=build_epilog(*results),
            **click_kwargs,
        )(wrapper)

        return cmd

    return decorator

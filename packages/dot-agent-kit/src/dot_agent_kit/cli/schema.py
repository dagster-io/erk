"""JSON schema documentation generation from dataclasses.

This module provides runtime introspection of dataclasses to generate
human-readable JSON schema documentation for CLI command help text.

Example usage:
    from dataclasses import dataclass
    from typing import Literal
    import click
    from dot_agent_kit.cli.schema import SchemaCommand, build_epilog

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

    @click.command(
        name="my-command",
        cls=SchemaCommand,
        epilog=build_epilog(SuccessResult, ErrorResult),
    )
    def my_command() -> None:
        '''Do something useful.'''
        ...
"""

import dataclasses
import types
import typing
from typing import Any, get_args, get_origin

import click


def format_type(hint: Any) -> str:
    """Convert Python type hint to readable string.

    Converts Python type annotations to human-readable strings for documentation.

    Args:
        hint: Type hint from typing module or built-in type

    Returns:
        Human-readable type string

    Examples:
        >>> format_type(bool)
        'boolean'
        >>> format_type(int)
        'integer'
        >>> format_type(str)
        'string'
        >>> format_type(list[str])
        'list[string]'
        >>> format_type(str | None)
        'string | null'
        >>> from typing import Literal
        >>> format_type(Literal["a", "b"])
        '"a" | "b"'
    """
    # Handle None type
    if hint is type(None):
        return "null"

    # Handle basic types
    if hint is bool:
        return "boolean"
    if hint is int:
        return "integer"
    if hint is float:
        return "number"
    if hint is str:
        return "string"
    if hint is list:
        return "list"
    if hint is dict:
        return "dict"

    # Get origin for generic types (list, dict, etc.)
    origin = get_origin(hint)

    # Handle Union types (including X | Y syntax and Optional)
    # Both typing.Union and types.UnionType (Python 3.10+ | operator)
    if origin is typing.Union or origin is types.UnionType:
        args = get_args(hint)
        formatted_args = [format_type(arg) for arg in args]
        return " | ".join(formatted_args)

    # Handle Literal types
    if origin is typing.Literal:
        args = get_args(hint)
        # Format literal values with quotes
        formatted_args = [f'"{arg}"' if isinstance(arg, str) else str(arg) for arg in args]
        return " | ".join(formatted_args)

    # Handle list[T]
    if origin is list:
        args = get_args(hint)
        if args:
            return f"list[{format_type(args[0])}]"
        return "list"

    # Handle dict[K, V]
    if origin is dict:
        args = get_args(hint)
        if args and len(args) == 2:
            key_type = format_type(args[0])
            value_type = format_type(args[1])
            return f"dict[{key_type}, {value_type}]"
        return "dict"

    # Fallback to string representation
    return str(hint)


def generate_schema(dc_class: type) -> str:
    """Generate schema documentation text from a dataclass.

    Uses dataclasses.fields() and typing.get_type_hints() to extract
    field names, types, and documentation from a dataclass.

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
    # Verify input is a dataclass
    if not dataclasses.is_dataclass(dc_class):
        raise TypeError(f"{dc_class.__name__} is not a dataclass")

    # Extract docstring for title (use class name as fallback)
    doc = dc_class.__doc__
    if doc:
        # Get first line of docstring, strip whitespace
        title = doc.strip().split("\n")[0]
    else:
        title = dc_class.__name__

    # Get type hints for all fields
    hints = typing.get_type_hints(dc_class)

    # Build field documentation lines
    lines = [title]
    for field in dataclasses.fields(dc_class):
        field_type = hints.get(field.name, Any)
        type_str = format_type(field_type)
        lines.append(f"  {field.name}: {type_str}")

    return "\n".join(lines)


def build_epilog(*dataclasses: type) -> str:
    """Combine multiple dataclass schemas into Click epilog text.

    Generates a "JSON Output Schema:" section suitable for Click command
    epilog parameter.

    Args:
        *dataclasses: One or more dataclass types to document

    Returns:
        Formatted epilog text with header and schemas

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Success:
        ...     '''Success result.'''
        ...     success: bool
        ...     data: str
        >>> @dataclass
        ... class Error:
        ...     '''Error result.'''
        ...     success: bool
        ...     message: str
        >>> print(build_epilog(Success, Error))
        JSON Output Schema:
        <BLANKLINE>
        Success result.
          success: boolean
          data: string
        <BLANKLINE>
        Error result.
          success: boolean
          message: string
    """
    schemas = [generate_schema(dc) for dc in dataclasses]
    return "JSON Output Schema:\n\n" + "\n\n".join(schemas)


class SchemaCommand(click.Command):
    """Click Command subclass that preserves newlines in epilog.

    By default, Click reformats epilog text and collapses newlines.
    This subclass preserves formatting for schema documentation.

    Usage:
        @click.command(
            name="my-command",
            cls=SchemaCommand,
            epilog=build_epilog(MyDataclass),
        )
        def my_command() -> None:
            pass
    """

    def format_epilog(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format epilog preserving original formatting.

        Overrides default Click behavior to preserve newlines and indentation
        in epilog text.
        """
        if self.epilog:
            # Preserve exact formatting by writing each line separately
            formatter.write_paragraph()
            for line in self.epilog.splitlines():
                formatter.write_text(line)

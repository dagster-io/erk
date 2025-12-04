"""Formatting utilities for JSON output schema in CLI help.

This module provides:
1. The @json_output decorator for kit CLI commands with typed JSON output
2. Functions to format TypedDict-based schemas for display in CLI help text

Usage:
    from dot_agent_kit.cli.schema_formatting import json_output

    class SuccessResult(TypedDict):
        success: Literal[True]
        value: str

    class ErrorResult(TypedDict):
        success: Literal[False]
        error: str

    @json_output(SuccessResult | ErrorResult)
    @click.command()
    def my_command():
        '''My command description.'''
        ...
"""

from collections.abc import Callable
from types import UnionType
from typing import Any, Literal, get_args, get_origin, get_type_hints

import click

# Attribute name used to store schema on decorated commands
JSON_OUTPUT_SCHEMA_ATTR = "_json_output_schema"


def json_output(
    schema: Any,  # TypedDict or Union of TypedDicts (e.g., Success | Error)
) -> Callable[[click.Command], click.Command]:
    """Decorator to mark a kit CLI command as having typed JSON output.

    This decorator:
    1. Stores the schema type on the command for runtime introspection
    2. Appends formatted schema documentation to the command's help text

    The schema should be a TypedDict or Union of TypedDicts that describes
    the JSON structure returned by the command.

    Args:
        schema: A TypedDict type or Union of TypedDict types (e.g., Success | Error)

    Returns:
        A decorator that marks the command with the schema

    Example:
        class MySuccess(TypedDict):
            success: Literal[True]
            data: str

        class MyError(TypedDict):
            success: Literal[False]
            error: str

        @json_output(MySuccess | MyError)
        @click.command()
        def my_command():
            '''My command that returns JSON.'''
            ...
    """

    def decorator(cmd: click.Command) -> click.Command:
        # Store schema on command for runtime access
        setattr(cmd, JSON_OUTPUT_SCHEMA_ATTR, schema)

        # Append schema documentation to help text
        schema_text = format_schema_for_help(schema)
        original_help = cmd.help or ""
        cmd.help = f"{original_help}{schema_text}"

        return cmd

    return decorator


def get_json_output_schema(
    cmd: click.Command,
) -> Any | None:  # Returns TypedDict or Union of TypedDicts
    """Get the JSON output schema from a decorated command.

    Args:
        cmd: A Click command that may have @json_output decorator

    Returns:
        The schema type if decorated, None otherwise
    """
    return getattr(cmd, JSON_OUTPUT_SCHEMA_ATTR, None)


def format_type_for_schema(
    type_hint: Any,  # type, Literal, UnionType, etc.
) -> str:
    """Format a type hint for schema display.

    Args:
        type_hint: A type hint to format (can be type, Literal, UnionType, etc.)

    Returns:
        Human-readable string representation
    """
    origin = get_origin(type_hint)

    # Handle Literal types - display as quoted values
    if origin is Literal:
        args = get_args(type_hint)
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, bool):
                return str(arg).lower()
            if isinstance(arg, str):
                return f'"{arg}"'
            return str(arg)
        formatted_args = []
        for arg in args:
            if isinstance(arg, bool):
                formatted_args.append(str(arg).lower())
            elif isinstance(arg, str):
                formatted_args.append(f'"{arg}"')
            else:
                formatted_args.append(str(arg))
        return " | ".join(formatted_args)

    # Handle Union types (X | Y)
    if origin is UnionType:
        args = get_args(type_hint)
        return " | ".join(format_type_for_schema(arg) for arg in args)

    # Handle basic types
    if type_hint is str:
        return "str"
    if type_hint is int:
        return "int"
    if type_hint is bool:
        return "bool"
    if type_hint is float:
        return "float"
    if type_hint is type(None):
        return "None"

    # Handle list, dict, etc.
    if origin is list:
        args = get_args(type_hint)
        if args:
            return f"list[{format_type_for_schema(args[0])}]"
        return "list"

    if origin is dict:
        args = get_args(type_hint)
        if len(args) == 2:
            return f"dict[{format_type_for_schema(args[0])}, {format_type_for_schema(args[1])}]"
        return "dict"

    # Fallback to type name
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__

    return str(type_hint)


def is_typeddict(cls: type) -> bool:
    """Check if a class is a TypedDict subclass.

    TypedDicts have __required_keys__ and __optional_keys__ attributes
    that regular dict subclasses don't have.

    Args:
        cls: A class to check

    Returns:
        True if the class is a TypedDict subclass, False otherwise
    """
    return (
        isinstance(cls, type)
        and issubclass(cls, dict)
        and hasattr(cls, "__required_keys__")
        and hasattr(cls, "__optional_keys__")
    )


def format_typeddict_for_schema(cls: type, indent: int = 2) -> list[str]:
    """Format a TypedDict class for schema display.

    Args:
        cls: A TypedDict subclass
        indent: Number of spaces for indentation

    Returns:
        List of formatted lines
    """
    lines: list[str] = []
    prefix = " " * indent

    # Get type hints for the TypedDict
    hints = get_type_hints(cls)

    # Determine success value if present
    success_hint = hints.get("success")
    success_value = ""
    if success_hint is not None:
        origin = get_origin(success_hint)
        if origin is Literal:
            args = get_args(success_hint)
            if args and isinstance(args[0], bool):
                success_value = f" (success={str(args[0]).lower()})"

    lines.append(f"{prefix}{cls.__name__}{success_value}:")

    # Format each field
    for field_name, field_type in hints.items():
        formatted_type = format_type_for_schema(field_type)
        lines.append(f"{prefix}  {field_name}: {formatted_type}")

    return lines


def format_schema_for_help(
    schema_type: Any,  # TypedDict or Union of TypedDicts
) -> str:
    """Format a schema type for help output.

    Args:
        schema_type: A TypedDict or Union of TypedDicts

    Returns:
        Formatted schema block for help text
    """
    lines: list[str] = ["", "Output Schema:"]

    origin = get_origin(schema_type)

    # Handle Union of TypedDicts (success/error variants)
    if origin is UnionType:
        variants = get_args(schema_type)
        for i, variant in enumerate(variants):
            if is_typeddict(variant):
                lines.extend(format_typeddict_for_schema(variant))
                # Add blank line between variants (but not after last)
                if i < len(variants) - 1:
                    lines.append("")
    # Handle single TypedDict
    elif is_typeddict(schema_type):
        lines.extend(format_typeddict_for_schema(schema_type))

    return "\n".join(lines)

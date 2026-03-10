"""JSON Schema generation for @json_command Click commands.

.. deprecated::
    This module is superseded by machine_schema.py. New commands should
    use @machine_command with machine_schema for schema generation.
    This module is retained for backwards compatibility with existing tests.

Provides:
- Click parameter type -> JSON Schema type mapping
- Input schema generation from Click command parameters
- Output schema generation from result types with json_schema() or plain dataclasses
- Full schema document assembly (input + output + error)
"""

from typing import Any

import click

from erk_shared.agentclick.dataclass_json import (
    ERROR_SCHEMA,
    output_schema,
    python_type_to_json_schema,
)
from erk_shared.agentclick.json_command import JsonCommandMeta

# Internal params injected by the decorator that should never appear in schemas
_INTERNAL_PARAMS = frozenset({"json_mode", "schema_mode", "ctx"})


def click_param_to_json_schema(param: click.Parameter) -> dict[str, Any]:
    """Convert a Click parameter to its JSON Schema representation.

    Args:
        param: A Click Parameter (Option or Argument)

    Returns:
        JSON Schema dict for the parameter's type
    """
    schema: dict[str, Any] = _click_type_to_schema(param.type, param)

    if isinstance(param, click.Option) and param.help:
        schema["description"] = param.help

    # Handle nargs=-1 (variadic arguments)
    if param.nargs == -1:
        inner = _click_type_to_schema(param.type, param)
        schema = {"type": "array", "items": inner}

    return schema


def _click_type_to_schema(click_type: click.ParamType, param: click.Parameter) -> dict[str, Any]:
    """Map a Click type to a JSON Schema type dict."""
    # Check for flag first (before type matching)
    if isinstance(param, click.Option) and param.is_flag:
        return {"type": "boolean"}

    if isinstance(click_type, click.types.IntParamType):
        return {"type": "integer"}

    if isinstance(click_type, click.types.FloatParamType):
        return {"type": "number"}

    if isinstance(click_type, click.types.BoolParamType):
        return {"type": "boolean"}

    if isinstance(click_type, click.Path):
        return {"type": "string", "format": "path"}

    if isinstance(click_type, click.Choice):
        return {"type": "string", "enum": list(click_type.choices)}

    # STRING and any unrecognized type default to string
    return {"type": "string"}


def command_input_schema(cmd: click.Command) -> dict[str, Any]:
    """Generate JSON Schema for a command's input parameters.

    Reads _json_command_meta from the command for exclude/required sets.
    Skips internal params (json_mode, schema_mode, ctx).

    Args:
        cmd: Click Command decorated with @json_command

    Returns:
        JSON Schema object with properties and required arrays
    """
    meta = _get_meta(cmd)

    skip_params = _INTERNAL_PARAMS | meta.exclude_json_input
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in cmd.params:
        if param.name is None or param.name in skip_params:
            continue

        properties[param.name] = click_param_to_json_schema(param)

        # Determine if required
        if param.name in meta.required_json_input:
            required.append(param.name)
        elif param.required:
            required.append(param.name)
        elif isinstance(param, click.Option) and param.default is None and not param.is_flag:
            # Options with no default and not explicitly required are optional
            pass

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = sorted(required)
    return schema


def output_type_schema(output_types: tuple[type, ...]) -> dict[str, Any]:
    """Generate JSON Schema for command output types.

    For each type:
    - If json_schema() classmethod exists, use it
    - Else if plain dataclass (no to_json_dict), auto-generate from fields
    - Else raise TypeError

    Single type returns schema directly. Multiple types wrap in oneOf.
    All output schemas include success: true (added by emit_json).

    Args:
        output_types: Tuple of result types

    Returns:
        JSON Schema object for the output
    """
    return output_schema(output_types)


def dataclass_to_json_schema(cls: type) -> dict[str, Any]:
    """Auto-generate JSON Schema from a plain dataclass's fields.

    Includes success: true since emit_json() adds it.

    Args:
        cls: A dataclass type

    Returns:
        JSON Schema object
    """
    from erk_shared.agentclick.dataclass_json import dataclass_result_schema

    return dataclass_result_schema(cls)


def _python_type_to_schema(type_hint: Any) -> dict[str, Any]:
    """Map a Python type annotation to JSON Schema."""
    return python_type_to_json_schema(type_hint)


def build_schema_document(cmd: click.Command) -> dict[str, Any]:
    """Build the full schema document for a @json_command.

    Returns a dict with command name, input_schema, output_schema, and error_schema.

    Args:
        cmd: Click Command decorated with @json_command

    Returns:
        Complete schema document
    """
    meta = _get_meta(cmd)

    return {
        "command": cmd.name,
        "input_schema": command_input_schema(cmd),
        "output_schema": output_type_schema(meta.output_types),
        "error_schema": ERROR_SCHEMA,
    }


def _get_meta(cmd: click.Command) -> JsonCommandMeta:
    """Read JsonCommandMeta from a command, with fallback for undecorated commands."""
    meta = getattr(cmd, "_json_command_meta", None)
    if meta is not None:
        return meta
    return JsonCommandMeta(
        exclude_json_input=frozenset(),
        required_json_input=frozenset(),
        output_types=(),
    )

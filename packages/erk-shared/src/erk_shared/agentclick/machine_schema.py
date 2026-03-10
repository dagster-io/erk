"""Schema generation for @machine_command from request/result dataclasses.

Derives schemas from dataclass fields (NOT from Click parameters).
This is the key difference from json_schema.py which used Click params.
"""

import dataclasses
import types
from typing import Any, Union, get_args, get_origin

from erk_shared.agentclick.json_schema import ERROR_SCHEMA, _python_type_to_schema
from erk_shared.agentclick.machine_command import MachineCommandMeta


def request_schema(request_type: type) -> dict[str, Any]:
    """Generate input schema from a frozen dataclass's fields.

    Args:
        request_type: A frozen dataclass type

    Returns:
        JSON Schema object with properties and required arrays
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in dataclasses.fields(request_type):
        field_schema = _python_type_to_schema(field.type)
        properties[field.name] = field_schema

        # Optional fields (X | None) are not required
        if _is_optional(field.type):
            continue

        # Fields with defaults are not required
        has_default = field.default is not dataclasses.MISSING
        has_factory = field.default_factory is not dataclasses.MISSING
        if has_default or has_factory:
            continue

        required.append(field.name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = sorted(required)
    return schema


def result_schema(result_types: tuple[type, ...]) -> dict[str, Any]:
    """Generate output schema for result types.

    Reuses the output_type_schema logic from json_schema.py.

    Args:
        result_types: Tuple of result dataclass types

    Returns:
        JSON Schema object for the output
    """
    from erk_shared.agentclick.json_schema import output_type_schema

    return output_type_schema(result_types)


def build_machine_schema_document(meta: MachineCommandMeta) -> dict[str, Any]:
    """Build the full schema document for a @machine_command.

    Args:
        meta: MachineCommandMeta from the command

    Returns:
        Complete schema document with command, description, input/output/error schemas
    """
    return {
        "command": meta.name,
        "description": meta.description,
        "input_schema": request_schema(meta.request_type),
        "output_schema": result_schema(meta.result_types),
        "error_schema": ERROR_SCHEMA,
    }


def _is_optional(type_hint: Any) -> bool:
    """Check if a type hint is Optional (X | None)."""
    origin = get_origin(type_hint)
    if origin is types.UnionType or origin is Union:
        return type(None) in get_args(type_hint)
    return False

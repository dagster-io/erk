"""JSON Schema generation utilities for dataclass-based types.

Provides:
- dataclass_to_json_schema() for auto-generating schema from dataclass fields
- output_type_schema() for generating output schema from result types
- ERROR_SCHEMA constant for error response format
- _python_type_to_schema() for mapping Python type annotations to JSON Schema
"""

import dataclasses
import types
from typing import Any, Union, get_args, get_origin

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean", "const": False},
        "error_type": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["success", "error_type", "message"],
}


# Python type to JSON Schema type mapping
_PYTHON_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


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
    if len(output_types) == 0:
        return {"type": "object", "properties": {"success": {"type": "boolean", "const": True}}}

    schemas = [_single_output_schema(t) for t in output_types]

    if len(schemas) == 1:
        return schemas[0]
    return {"oneOf": schemas}


def _single_output_schema(cls: type) -> dict[str, Any]:
    """Generate JSON Schema for a single output type."""
    json_schema_method = getattr(cls, "json_schema", None)
    if json_schema_method is not None:
        return json_schema_method()

    if dataclasses.is_dataclass(cls):
        return dataclass_to_json_schema(cls)

    raise TypeError(
        f"Cannot generate schema for {cls.__name__}: "
        "no json_schema() classmethod and not a dataclass"
    )


def dataclass_to_json_schema(cls: type) -> dict[str, Any]:
    """Auto-generate JSON Schema from a plain dataclass's fields.

    Includes success: true since emit_json() adds it.

    Args:
        cls: A dataclass type

    Returns:
        JSON Schema object
    """
    properties: dict[str, Any] = {"success": {"type": "boolean", "const": True}}
    required: list[str] = ["success"]

    for field in dataclasses.fields(cls):
        field_schema = _python_type_to_schema(field.type)
        properties[field.name] = field_schema
        required.append(field.name)

    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }


def _python_type_to_schema(type_hint: Any) -> dict[str, Any]:
    """Map a Python type annotation to JSON Schema."""
    # Handle direct type matches
    if type_hint in _PYTHON_TYPE_MAP:
        return {"type": _PYTHON_TYPE_MAP[type_hint]}

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Handle X | None (types.UnionType) and typing.Optional[X] (typing.Union)
    if origin is types.UnionType or origin is Union:
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1 and non_none[0] in _PYTHON_TYPE_MAP:
                return {"type": [_PYTHON_TYPE_MAP[non_none[0]], "null"]}
        return {"type": "string"}

    # list[X]
    if origin is list and len(args) == 1:
        items_schema = _python_type_to_schema(args[0])
        return {"type": "array", "items": items_schema}

    # dict[str, X]
    if origin is dict:
        return {"type": "object"}

    # Fallback
    return {"type": "string"}

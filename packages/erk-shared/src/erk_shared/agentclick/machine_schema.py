"""Schema generation for @machine_command decorators.

Generates JSON Schema documents from frozen dataclass request types
and result types, independent of Click parameters.
"""

import dataclasses
import types
from typing import Any, Literal, get_args, get_origin

from erk_shared.agentclick.machine_command import MachineCommandMeta

# Shared error schema (same shape as MachineCommandError serialization)
ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean", "const": False},
        "error_type": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["error_type", "message", "success"],
}

# Python type to JSON Schema type mapping
_PYTHON_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def request_schema(request_type: type) -> dict[str, Any]:
    """Generate JSON Schema for a machine command's input (request dataclass).

    Args:
        request_type: Frozen dataclass type

    Returns:
        JSON Schema object with properties and required arrays
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in dataclasses.fields(request_type):
        field_schema = _python_type_to_schema(field.type)
        properties[field.name] = field_schema

        # Field is required if it has no default and no default_factory
        has_default = field.default is not dataclasses.MISSING
        has_factory = field.default_factory is not dataclasses.MISSING
        is_optional_type = _is_optional_type(field.type)

        if not has_default and not has_factory and not is_optional_type:
            required.append(field.name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = sorted(required)
    return schema


def result_schema(result_types: tuple[type, ...]) -> dict[str, Any]:
    """Generate JSON Schema for command output types.

    Single type returns schema directly. Multiple types wrap in oneOf.
    All output schemas include success: true.

    Args:
        result_types: Tuple of result types

    Returns:
        JSON Schema object for the output
    """
    if len(result_types) == 0:
        return {"type": "object", "properties": {"success": {"type": "boolean", "const": True}}}

    schemas = [_single_output_schema(t) for t in result_types]

    if len(schemas) == 1:
        return schemas[0]
    return {"oneOf": schemas}


def build_machine_schema_document(meta: MachineCommandMeta) -> dict[str, Any]:
    """Build the full schema document for a @machine_command.

    Returns a dict with input_schema, output_schema, and error_schema.

    Args:
        meta: MachineCommandMeta with request_type and output_types

    Returns:
        Complete schema document
    """
    return {
        "input_schema": request_schema(meta.request_type),
        "output_schema": result_schema(meta.output_types),
        "error_schema": ERROR_SCHEMA,
    }


def _single_output_schema(cls: type) -> dict[str, Any]:
    """Generate JSON Schema for a single output type."""
    json_schema_method = getattr(cls, "json_schema", None)
    if json_schema_method is not None:
        return json_schema_method()

    if dataclasses.is_dataclass(cls):
        return _dataclass_to_result_schema(cls)

    raise TypeError(
        f"Cannot generate schema for {cls.__name__}: "
        "no json_schema() classmethod and not a dataclass"
    )


def _dataclass_to_result_schema(cls: type) -> dict[str, Any]:
    """Auto-generate JSON Schema from a result dataclass's fields.

    Includes success: true since emit_machine_result() adds it.
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
    # Direct type matches
    if type_hint in _PYTHON_TYPE_MAP:
        return {"type": _PYTHON_TYPE_MAP[type_hint]}

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Literal -> enum
    if origin is Literal:
        return {"type": "string", "enum": list(args)}

    # X | None (UnionType)
    if origin is types.UnionType:
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                inner = _python_type_to_schema(non_none[0])
                if "type" in inner and isinstance(inner["type"], str):
                    return {"type": [inner["type"], "null"]}
                return inner
        return {"type": "string"}

    # tuple[X, ...]
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        items_schema = _python_type_to_schema(args[0])
        return {"type": "array", "items": items_schema}

    # list[X]
    if origin is list and len(args) == 1:
        items_schema = _python_type_to_schema(args[0])
        return {"type": "array", "items": items_schema}

    # dict[K, V]
    if origin is dict:
        return {"type": "object"}

    # Fallback
    return {"type": "string"}


def _is_optional_type(type_hint: Any) -> bool:
    """Check if a type hint is X | None."""
    origin = get_origin(type_hint)
    if origin is types.UnionType:
        return type(None) in get_args(type_hint)
    return False

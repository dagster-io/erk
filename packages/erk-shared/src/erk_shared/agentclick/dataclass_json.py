"""Generic JSON <-> frozen-dataclass utilities.

No Click dependency. Shared by both @json_command and @machine_command.
"""

import dataclasses
import json
import sys
import types
from dataclasses import fields
from typing import Any, Literal, Union, get_args, get_origin

# --- Constants ---

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean", "const": False},
        "error_type": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["error_type", "message", "success"],
}

PYTHON_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


# --- Schema: Python type -> JSON Schema ---


def python_type_to_json_schema(type_hint: Any) -> dict[str, Any]:
    """Map a Python type annotation to JSON Schema.

    Handles: Literal, tuple[X,...], list[X], dict, UnionType, typing.Union, primitives.
    """
    # Direct type matches
    if type_hint in PYTHON_TYPE_MAP:
        return {"type": PYTHON_TYPE_MAP[type_hint]}

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Literal -> enum
    if origin is Literal:
        return {"type": "string", "enum": list(args)}

    # X | None (UnionType) and typing.Optional[X] (typing.Union)
    if origin is types.UnionType or origin is Union:
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                inner = python_type_to_json_schema(non_none[0])
                if "type" in inner and isinstance(inner["type"], str):
                    return {"type": [inner["type"], "null"]}
                return inner
        return {"type": "string"}

    # tuple[X, ...]
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        items_schema = python_type_to_json_schema(args[0])
        return {"type": "array", "items": items_schema}

    # list[X]
    if origin is list and len(args) == 1:
        items_schema = python_type_to_json_schema(args[0])
        return {"type": "array", "items": items_schema}

    # dict[K, V]
    if origin is dict:
        return {"type": "object"}

    # Fallback
    return {"type": "string"}


def dataclass_result_schema(cls: type) -> dict[str, Any]:
    """Auto-generate JSON Schema from a result dataclass's fields.

    Always includes success: true (output schema convention).
    """
    properties: dict[str, Any] = {"success": {"type": "boolean", "const": True}}
    required: list[str] = ["success"]

    for field in dataclasses.fields(cls):
        field_schema = python_type_to_json_schema(field.type)
        properties[field.name] = field_schema
        required.append(field.name)

    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }


def output_schema(output_types: tuple[type, ...]) -> dict[str, Any]:
    """Generate JSON Schema for command output types.

    Single type returns schema directly. Multiple types wrap in oneOf.
    All output schemas include success: true.
    """
    if len(output_types) == 0:
        return {"type": "object", "properties": {"success": {"type": "boolean", "const": True}}}

    schemas = [_single_output_schema(t) for t in output_types]

    if len(schemas) == 1:
        return schemas[0]
    return {"oneOf": schemas}


def is_optional_type(type_hint: Any) -> bool:
    """Check if a type hint is X | None."""
    origin = get_origin(type_hint)
    if origin is types.UnionType:
        return type(None) in get_args(type_hint)
    return False


# --- Deserialization: JSON dict -> dataclass ---


def coerce_json_value(value: Any, target_type: Any) -> Any:
    """Coerce a JSON value to the expected Python type.

    Handles: Literal, tuple, list, dict, bool, int, float, str,
    X | None unions, and passes through unrecognized types.
    """
    origin = get_origin(target_type)
    args = get_args(target_type)

    # Literal validation
    if origin is Literal:
        if value not in args:
            raise ValueError(f"Invalid value {value!r}, expected one of {args}")
        return value

    # tuple[X, ...] from JSON arrays
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        if isinstance(value, list):
            return tuple(coerce_json_value(v, args[0]) for v in value)
        return value

    # list[X]
    if origin is list and len(args) == 1:
        if isinstance(value, list):
            return [coerce_json_value(v, args[0]) for v in value]
        return value

    # dict[K, V]
    if origin is dict:
        return value

    # Union types (X | None)
    if origin is types.UnionType:
        if value is None and type(None) in args:
            return None
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return coerce_json_value(value, non_none[0])
        return value

    # bool must be checked before int (bool is subclass of int)
    if target_type is bool:
        if isinstance(value, bool):
            return value
        raise ValueError(f"Expected boolean, got {type(value).__name__}")

    if target_type is int:
        if isinstance(value, bool):
            raise ValueError("Expected integer, got boolean")
        if isinstance(value, int):
            return value
        return value

    if target_type is float:
        if isinstance(value, (int, float)):
            return float(value)
        return value

    if target_type is str:
        if isinstance(value, str):
            return value
        return value

    return value


def parse_dataclass_from_json(cls: type, data: dict[str, Any]) -> Any:
    """Parse a JSON dict into a frozen dataclass instance.

    Checks for from_json_dict() classmethod first. Falls back to
    generic dataclass construction with strict validation.
    """
    from_json = getattr(cls, "from_json_dict", None)
    if from_json is not None:
        return from_json(data)
    return _build_dataclass_request(cls, data)


# --- Serialization: dataclass -> JSON dict ---


def serialize_to_json_dict(result: Any) -> dict[str, Any]:
    """Serialize a result to a JSON-compatible dict.

    Checks for to_json_dict() protocol first, falls back to
    dataclasses.asdict() for plain dataclasses.
    """
    if hasattr(result, "to_json_dict"):
        return result.to_json_dict()
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return dataclasses.asdict(result)
    raise TypeError(
        f"Cannot serialize {type(result).__name__}: no to_json_dict() and not a dataclass"
    )


# --- I/O ---


def read_json_stdin() -> dict[str, Any] | None:
    """Read JSON input from stdin.

    Returns None if stdin is a TTY (interactive) or empty.

    Raises:
        json.JSONDecodeError: If stdin contains invalid JSON
        ValueError: If stdin JSON is not an object
    """
    if sys.stdin.isatty():
        return None
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


def emit_json_success(data: dict[str, Any]) -> None:
    """Emit a JSON success result to stdout. Adds success=True automatically."""
    import click

    data["success"] = True
    click.echo(json.dumps(data, indent=2))


def emit_json_error(*, error_type: str, message: str) -> None:
    """Emit a structured error to stdout."""
    import click

    data = {"success": False, "error_type": error_type, "message": message}
    click.echo(json.dumps(data, indent=2))


# --- Private helpers ---


def _single_output_schema(cls: type) -> dict[str, Any]:
    """Generate JSON Schema for a single output type."""
    json_schema_method = getattr(cls, "json_schema", None)
    if json_schema_method is not None:
        return json_schema_method()

    if dataclasses.is_dataclass(cls):
        return dataclass_result_schema(cls)

    raise TypeError(
        f"Cannot generate schema for {cls.__name__}: "
        "no json_schema() classmethod and not a dataclass"
    )


def _build_dataclass_request(request_type: type, data: dict[str, Any]) -> Any:
    """Build a dataclass from JSON dict with strict validation.

    - Rejects unknown keys
    - Applies type coercion
    - Fills in defaults for missing fields
    """
    valid_fields = {f.name: f for f in fields(request_type)}

    # Reject unknown keys
    for key in data:
        if key not in valid_fields:
            raise ValueError(f"Unknown field: {key}")

    kwargs: dict[str, Any] = {}
    for name, field in valid_fields.items():
        if name in data:
            kwargs[name] = coerce_json_value(data[name], field.type)
        elif field.default is not dataclasses.MISSING:
            kwargs[name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            kwargs[name] = field.default_factory()
        else:
            raise ValueError(f"Missing required field: {name}")

    return request_type(**kwargs)

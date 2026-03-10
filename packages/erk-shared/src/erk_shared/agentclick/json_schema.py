"""Schema helpers for explicit machine commands."""

from __future__ import annotations

import dataclasses
import json
import types
from dataclasses import MISSING
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

import click

from erk_shared.agentclick.machine_command import MachineCommandMeta

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean", "const": False},
        "error_type": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["success", "error_type", "message"],
}


def build_schema_document(cmd: click.Command) -> dict[str, Any]:
    """Build the full schema document for a machine command."""

    meta = _get_meta(cmd)
    return {
        "command": cmd.name,
        "input_schema": command_input_schema(cmd),
        "output_schema": output_type_schema(meta.output_types),
        "error_schema": ERROR_SCHEMA,
    }


def command_input_schema(cmd: click.Command) -> dict[str, Any]:
    """Build the input schema for a machine command."""

    meta = _get_meta(cmd)
    request_type = meta.request_type
    request_schema_method = getattr(request_type, "json_schema", None)
    if callable(request_schema_method):
        return request_schema_method()

    if not dataclasses.is_dataclass(request_type):
        raise TypeError(f"Request type {request_type.__name__} must be a dataclass")

    return dataclass_input_schema(request_type)


def output_type_schema(output_types: tuple[type, ...]) -> dict[str, Any]:
    """Build the success output schema for a machine command."""

    if len(output_types) == 0:
        return {
            "type": "object",
            "properties": {"success": {"type": "boolean", "const": True}},
            "required": ["success"],
        }

    schemas = [_single_output_schema(output_type) for output_type in output_types]
    if len(schemas) == 1:
        return schemas[0]
    return {"oneOf": schemas}


def dataclass_input_schema(cls: type) -> dict[str, Any]:
    """Auto-generate input schema from a dataclass request type."""

    properties: dict[str, Any] = {}
    required: list[str] = []
    field_types = _dataclass_field_types(cls)

    for field in dataclasses.fields(cls):
        field_type = field_types.get(field.name, field.type)
        field_schema = _python_type_to_schema(field_type)
        if field.default is not MISSING:
            field_schema["default"] = _json_default(field.default)
        elif field.default_factory is not MISSING:
            field_schema["default"] = _json_default(field.default_factory())
        elif not _allows_none(field_type):
            required.append(field.name)

        properties[field.name] = field_schema

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = sorted(required)
    return schema


def dataclass_output_schema(cls: type) -> dict[str, Any]:
    """Auto-generate success output schema from a dataclass result type."""

    properties: dict[str, Any] = {"success": {"type": "boolean", "const": True}}
    required = ["success"]
    field_types = _dataclass_field_types(cls)

    for field in dataclasses.fields(cls):
        field_type = field_types.get(field.name, field.type)
        properties[field.name] = _python_type_to_schema(field_type)
        required.append(field.name)

    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }


def _single_output_schema(output_type: type) -> dict[str, Any]:
    output_schema_method = getattr(output_type, "json_schema", None)
    if callable(output_schema_method):
        return output_schema_method()

    if dataclasses.is_dataclass(output_type):
        return dataclass_output_schema(output_type)

    raise TypeError(
        f"Cannot generate schema for {output_type.__name__}: "
        "no json_schema() classmethod and not a dataclass"
    )


def _python_type_to_schema(type_hint: Any) -> dict[str, Any]:
    if type_hint is Any:
        return {}

    if type_hint is bool:
        return {"type": "boolean"}
    if type_hint is int:
        return {"type": "integer"}
    if type_hint is float:
        return {"type": "number"}
    if type_hint is str:
        return {"type": "string"}

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin is Literal:
        literal_values = list(args)
        schema = {"enum": literal_values}
        if literal_values:
            schema["type"] = _python_value_to_json_type(literal_values[0])
        return schema

    if origin in (types.UnionType, Union):
        non_none_types = [arg for arg in args if arg is not type(None)]
        if type(None) in args and len(non_none_types) == 1:
            schema = _python_type_to_schema(non_none_types[0])
            schema_type = schema.get("type")
            if isinstance(schema_type, str):
                schema["type"] = [schema_type, "null"]
            return schema
        return {"oneOf": [_python_type_to_schema(arg) for arg in args]}

    if origin in (list, tuple):
        item_type = args[0] if args else Any
        return {"type": "array", "items": _python_type_to_schema(item_type)}

    if origin is dict:
        return {"type": "object"}

    if dataclasses.is_dataclass(type_hint):
        return dataclass_input_schema(type_hint)

    return {"type": "string"}


def _python_value_to_json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return "string"


def _allows_none(type_hint: Any) -> bool:
    origin = get_origin(type_hint)
    if origin not in (types.UnionType, Union):
        return False
    return type(None) in get_args(type_hint)


def _get_meta(cmd: click.Command) -> MachineCommandMeta:
    meta = getattr(cmd, "_machine_command_meta", None)
    if meta is None:
        raise TypeError(f"{cmd.name} is not a machine command")
    return meta


def _dataclass_field_types(cls: type) -> dict[str, Any]:
    return get_type_hints(cls, include_extras=True)


def _json_default(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    try:
        json.dumps(value)
    except TypeError:
        return None
    return value

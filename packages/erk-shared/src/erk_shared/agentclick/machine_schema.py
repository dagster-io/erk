"""Schema generation for @machine_command decorators.

Generates JSON Schema documents from frozen dataclass request types
and result types, independent of Click parameters.
"""

import dataclasses
from typing import Any

from erk_shared.agentclick.dataclass_json import (
    ERROR_SCHEMA,
    is_optional_type,
    output_schema,
    python_type_to_json_schema,
)
from erk_shared.agentclick.machine_command import MachineCommandMeta


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
        field_schema = python_type_to_json_schema(field.type)
        properties[field.name] = field_schema

        # Field is required if it has no default and no default_factory
        has_default = field.default is not dataclasses.MISSING
        has_factory = field.default_factory is not dataclasses.MISSING
        is_optional = is_optional_type(field.type)

        if not has_default and not has_factory and not is_optional:
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
    return output_schema(result_types)


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

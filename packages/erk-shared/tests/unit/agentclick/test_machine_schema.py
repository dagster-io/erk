"""Tests for machine_schema.py - JSON Schema generation for @machine_command."""

from dataclasses import dataclass
from typing import Any

from erk_shared.agentclick.machine_command import MachineCommandMeta
from erk_shared.agentclick.machine_schema import (
    ERROR_SCHEMA,
    build_machine_schema_document,
    request_schema,
    result_schema,
)


@dataclass(frozen=True)
class MinimalRequest:
    prompt: str


@dataclass(frozen=True)
class FullRequest:
    prompt: str
    count: int
    verbose: bool
    model: str | None = None


@dataclass(frozen=True)
class SimpleResult:
    answer: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"answer": self.answer}


@dataclass(frozen=True)
class ResultWithSchema:
    value: int

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "const": True},
                "value": {"type": "integer"},
            },
            "required": ["success", "value"],
        }


def test_request_schema_minimal() -> None:
    """Minimal request generates correct schema."""
    schema = request_schema(MinimalRequest)
    assert schema["type"] == "object"
    assert "prompt" in schema["properties"]
    assert schema["properties"]["prompt"]["type"] == "string"
    assert schema["required"] == ["prompt"]


def test_request_schema_full() -> None:
    """Full request with multiple types generates correct schema."""
    schema = request_schema(FullRequest)
    assert schema["type"] == "object"
    props = schema["properties"]
    assert props["prompt"]["type"] == "string"
    assert props["count"]["type"] == "integer"
    assert props["verbose"]["type"] == "boolean"
    assert props["model"]["type"] == ["string", "null"]
    # model has a default (None) so it's not required
    assert sorted(schema["required"]) == ["count", "prompt", "verbose"]


def test_request_schema_optional_not_required() -> None:
    """Fields with X | None type are not marked as required."""
    schema = request_schema(FullRequest)
    assert "model" not in schema["required"]


def test_result_schema_empty() -> None:
    """Empty output_types returns basic success schema."""
    schema = result_schema(())
    assert schema["type"] == "object"
    assert schema["properties"]["success"]["const"] is True


def test_result_schema_single_type() -> None:
    """Single output type returns schema directly (no oneOf)."""
    schema = result_schema((SimpleResult,))
    assert "oneOf" not in schema
    assert schema["type"] == "object"
    assert "answer" in schema["properties"]
    assert "success" in schema["properties"]


def test_result_schema_custom_json_schema() -> None:
    """Result with json_schema() classmethod uses custom schema."""
    schema = result_schema((ResultWithSchema,))
    assert schema["properties"]["value"]["type"] == "integer"
    assert "success" in schema["properties"]


def test_result_schema_multiple_types() -> None:
    """Multiple output types wraps in oneOf."""
    schema = result_schema((SimpleResult, ResultWithSchema))
    assert "oneOf" in schema
    assert len(schema["oneOf"]) == 2


def test_build_machine_schema_document() -> None:
    """build_machine_schema_document includes all three sections."""
    meta = MachineCommandMeta(request_type=MinimalRequest, output_types=(SimpleResult,))
    doc = build_machine_schema_document(meta)
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert "error_schema" in doc
    assert doc["error_schema"] == ERROR_SCHEMA


def test_error_schema_structure() -> None:
    """Error schema includes success, error_type, message."""
    assert ERROR_SCHEMA["type"] == "object"
    assert ERROR_SCHEMA["properties"]["success"]["const"] is False
    assert "error_type" in ERROR_SCHEMA["properties"]
    assert "message" in ERROR_SCHEMA["properties"]

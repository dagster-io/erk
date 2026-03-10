"""Tests for machine schema generation from request/result dataclasses."""

from dataclasses import dataclass
from typing import Any

from erk_shared.agentclick.json_schema import (
    ERROR_SCHEMA,
    dataclass_to_json_schema,
    output_type_schema,
)
from erk_shared.agentclick.machine_command import MachineCommandMeta
from erk_shared.agentclick.machine_schema import (
    build_machine_schema_document,
    request_schema,
    result_schema,
)

# -- request_schema tests --


def test_request_schema_basic_fields() -> None:
    @dataclass(frozen=True)
    class Request:
        prompt: str
        count: int
        rate: float
        verbose: bool

    schema = request_schema(Request)
    assert schema["properties"]["prompt"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["rate"]["type"] == "number"
    assert schema["properties"]["verbose"]["type"] == "boolean"


def test_request_schema_required_fields() -> None:
    @dataclass(frozen=True)
    class Request:
        prompt: str
        model: str | None = None

    schema = request_schema(Request)
    assert "prompt" in schema["required"]
    assert "model" not in schema.get("required", [])


def test_request_schema_optional_union_fields() -> None:
    @dataclass(frozen=True)
    class Request:
        name: str | None = None

    schema = request_schema(Request)
    assert schema["properties"]["name"]["type"] == ["string", "null"]
    # Optional fields should not be required
    assert "required" not in schema or "name" not in schema["required"]


def test_request_schema_fields_with_defaults() -> None:
    @dataclass(frozen=True)
    class Request:
        dry_run: bool = False
        limit: int = 10

    schema = request_schema(Request)
    # Fields with defaults are not required
    assert "required" not in schema or len(schema.get("required", [])) == 0


def test_request_schema_list_field() -> None:
    @dataclass(frozen=True)
    class Request:
        labels: list[str]

    schema = request_schema(Request)
    assert schema["properties"]["labels"]["type"] == "array"
    assert schema["properties"]["labels"]["items"]["type"] == "string"


def test_request_schema_dict_field() -> None:
    @dataclass(frozen=True)
    class Request:
        metadata: dict[str, Any]

    schema = request_schema(Request)
    assert schema["properties"]["metadata"]["type"] == "object"


# -- result_schema tests --


def test_result_schema_delegates_to_output_type_schema() -> None:
    @dataclass(frozen=True)
    class Result:
        value: int

    schema = result_schema((Result,))
    assert "value" in schema["properties"]
    assert "success" in schema["properties"]


# -- output_type_schema tests (kept from old test_json_schema) --


def test_output_schema_with_json_schema_classmethod() -> None:
    @dataclass(frozen=True)
    class MyResult:
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

    schema = output_type_schema((MyResult,))
    assert schema["properties"]["value"]["type"] == "integer"


def test_output_schema_plain_dataclass() -> None:
    @dataclass(frozen=True)
    class PlainResult:
        name: str
        count: int

    schema = output_type_schema((PlainResult,))
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["success"]["const"] is True


def test_output_schema_multiple_types_uses_oneof() -> None:
    @dataclass(frozen=True)
    class ResultA:
        a: str

    @dataclass(frozen=True)
    class ResultB:
        b: int

    schema = output_type_schema((ResultA, ResultB))
    assert "oneOf" in schema
    assert len(schema["oneOf"]) == 2


def test_output_schema_empty_types() -> None:
    schema = output_type_schema(())
    assert schema["properties"]["success"]["const"] is True


# -- dataclass_to_json_schema tests --


def test_dataclass_schema_basic_fields() -> None:
    @dataclass(frozen=True)
    class Simple:
        name: str
        count: int
        rate: float
        active: bool

    schema = dataclass_to_json_schema(Simple)
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["rate"]["type"] == "number"
    assert schema["properties"]["active"]["type"] == "boolean"
    assert "success" in schema["properties"]


def test_dataclass_schema_optional_field() -> None:
    @dataclass(frozen=True)
    class WithOptional:
        name: str
        label: str | None

    schema = dataclass_to_json_schema(WithOptional)
    assert schema["properties"]["label"]["type"] == ["string", "null"]


# -- build_machine_schema_document tests --


def test_build_machine_schema_document_structure() -> None:
    @dataclass(frozen=True)
    class MyRequest:
        prompt: str

    @dataclass(frozen=True)
    class MyResult:
        value: int

    meta = MachineCommandMeta(
        request_type=MyRequest,
        result_types=(MyResult,),
        name="my_tool",
        description="A test tool",
    )

    doc = build_machine_schema_document(meta)
    assert doc["command"] == "my_tool"
    assert doc["description"] == "A test tool"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert doc["error_schema"] == ERROR_SCHEMA


def test_build_machine_schema_document_input_from_request() -> None:
    @dataclass(frozen=True)
    class MyRequest:
        prompt: str
        model: str | None = None

    meta = MachineCommandMeta(
        request_type=MyRequest,
        result_types=(),
        name="tool",
        description="desc",
    )

    doc = build_machine_schema_document(meta)
    assert "prompt" in doc["input_schema"]["properties"]
    assert "model" in doc["input_schema"]["properties"]
    assert "prompt" in doc["input_schema"]["required"]


# -- ERROR_SCHEMA constant --


def test_error_schema_structure() -> None:
    assert ERROR_SCHEMA["type"] == "object"
    assert "success" in ERROR_SCHEMA["properties"]
    assert "error_type" in ERROR_SCHEMA["properties"]
    assert "message" in ERROR_SCHEMA["properties"]
    assert ERROR_SCHEMA["properties"]["success"]["const"] is False

"""Tests for JSON Schema utility functions."""

from dataclasses import dataclass
from typing import Any

from erk_shared.agentclick.json_schema import (
    ERROR_SCHEMA,
    _python_type_to_schema,
    dataclass_to_json_schema,
    output_type_schema,
)

# -- _python_type_to_schema tests --


def test_python_type_string() -> None:
    assert _python_type_to_schema(str) == {"type": "string"}


def test_python_type_int() -> None:
    assert _python_type_to_schema(int) == {"type": "integer"}


def test_python_type_float() -> None:
    assert _python_type_to_schema(float) == {"type": "number"}


def test_python_type_bool() -> None:
    assert _python_type_to_schema(bool) == {"type": "boolean"}


def test_python_type_optional() -> None:
    assert _python_type_to_schema(str | None) == {"type": ["string", "null"]}


def test_python_type_list() -> None:
    schema = _python_type_to_schema(list[str])
    assert schema == {"type": "array", "items": {"type": "string"}}


def test_python_type_dict() -> None:
    assert _python_type_to_schema(dict[str, Any]) == {"type": "object"}


# -- output_type_schema tests --


def test_output_schema_single_type() -> None:
    @dataclass(frozen=True)
    class Result:
        value: int

    schema = output_type_schema((Result,))
    assert schema["properties"]["value"]["type"] == "integer"
    assert schema["properties"]["success"]["const"] is True


def test_output_schema_multiple_types() -> None:
    @dataclass(frozen=True)
    class A:
        a: str

    @dataclass(frozen=True)
    class B:
        b: int

    schema = output_type_schema((A, B))
    assert "oneOf" in schema
    assert len(schema["oneOf"]) == 2


def test_output_schema_empty() -> None:
    schema = output_type_schema(())
    assert schema["properties"]["success"]["const"] is True


# -- dataclass_to_json_schema tests --


def test_dataclass_schema() -> None:
    @dataclass(frozen=True)
    class Simple:
        name: str
        count: int

    schema = dataclass_to_json_schema(Simple)
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert "success" in schema["properties"]


# -- ERROR_SCHEMA --


def test_error_schema() -> None:
    assert ERROR_SCHEMA["properties"]["success"]["const"] is False
    assert "error_type" in ERROR_SCHEMA["properties"]
    assert "message" in ERROR_SCHEMA["properties"]

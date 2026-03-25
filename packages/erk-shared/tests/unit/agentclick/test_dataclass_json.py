"""Tests for dataclass_json.py - shared JSON <-> dataclass utilities."""

from dataclasses import dataclass
from typing import Any, Literal

from erk_shared.agentclick.dataclass_json import (
    ERROR_SCHEMA,
    PYTHON_TYPE_MAP,
    coerce_json_value,
    dataclass_result_schema,
    is_optional_type,
    output_schema,
    parse_dataclass_from_json,
    python_type_to_json_schema,
    serialize_to_json_dict,
)

# --- Test fixtures ---


@dataclass(frozen=True)
class PointResult:
    x: int
    y: int


@dataclass(frozen=True)
class TaggedResult:
    tag: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"tag": self.tag}


@dataclass(frozen=True)
class WithJsonSchema:
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


@dataclass(frozen=True)
class RequestWithOptional:
    name: str
    label: str | None = None


@dataclass(frozen=True)
class RequestWithFromJson:
    name: str

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "RequestWithFromJson":
        return cls(name=data["name"].upper())


# --- Constants ---


def test_error_schema_structure() -> None:
    assert ERROR_SCHEMA["type"] == "object"
    assert ERROR_SCHEMA["properties"]["success"]["const"] is False
    assert "error_type" in ERROR_SCHEMA["properties"]
    assert "message" in ERROR_SCHEMA["properties"]


def test_python_type_map_entries() -> None:
    assert PYTHON_TYPE_MAP[str] == "string"
    assert PYTHON_TYPE_MAP[int] == "integer"
    assert PYTHON_TYPE_MAP[float] == "number"
    assert PYTHON_TYPE_MAP[bool] == "boolean"


# --- python_type_to_json_schema ---


def test_python_type_to_json_schema_primitives() -> None:
    assert python_type_to_json_schema(str) == {"type": "string"}
    assert python_type_to_json_schema(int) == {"type": "integer"}
    assert python_type_to_json_schema(float) == {"type": "number"}
    assert python_type_to_json_schema(bool) == {"type": "boolean"}


def test_python_type_to_json_schema_literal() -> None:
    schema = python_type_to_json_schema(Literal["a", "b"])
    assert schema == {"type": "string", "enum": ["a", "b"]}


def test_python_type_to_json_schema_optional_union_type() -> None:
    schema = python_type_to_json_schema(str | None)
    assert schema == {"type": ["string", "null"]}


def test_python_type_to_json_schema_optional() -> None:
    """Verify str | None produces nullable schema."""
    schema = python_type_to_json_schema(str | None)
    assert schema == {"type": ["string", "null"]}


def test_python_type_to_json_schema_tuple() -> None:
    schema = python_type_to_json_schema(tuple[str, ...])
    assert schema == {"type": "array", "items": {"type": "string"}}


def test_python_type_to_json_schema_list() -> None:
    schema = python_type_to_json_schema(list[int])
    assert schema == {"type": "array", "items": {"type": "integer"}}


def test_python_type_to_json_schema_dict() -> None:
    schema = python_type_to_json_schema(dict[str, Any])
    assert schema == {"type": "object"}


# --- dataclass_result_schema ---


def test_dataclass_result_schema_includes_success() -> None:
    schema = dataclass_result_schema(PointResult)
    assert schema["properties"]["success"]["const"] is True
    assert "success" in schema["required"]


def test_dataclass_result_schema_includes_fields() -> None:
    schema = dataclass_result_schema(PointResult)
    assert schema["properties"]["x"]["type"] == "integer"
    assert schema["properties"]["y"]["type"] == "integer"


# --- output_schema ---


def test_output_schema_empty() -> None:
    schema = output_schema(())
    assert schema["properties"]["success"]["const"] is True


def test_output_schema_single() -> None:
    schema = output_schema((PointResult,))
    assert "oneOf" not in schema
    assert "x" in schema["properties"]


def test_output_schema_multiple() -> None:
    schema = output_schema((PointResult, WithJsonSchema))
    assert "oneOf" in schema
    assert len(schema["oneOf"]) == 2


def test_output_schema_custom_json_schema() -> None:
    schema = output_schema((WithJsonSchema,))
    assert schema["properties"]["value"]["type"] == "integer"


# --- is_optional_type ---


def test_is_optional_type_true() -> None:
    assert is_optional_type(str | None) is True


def test_is_optional_type_false_for_plain() -> None:
    assert is_optional_type(str) is False


# --- coerce_json_value ---


def test_coerce_json_value_literal() -> None:
    assert coerce_json_value("a", Literal["a", "b"]) == "a"


def test_coerce_json_value_tuple() -> None:
    result = coerce_json_value(["a", "b"], tuple[str, ...])
    assert result == ("a", "b")


def test_coerce_json_value_list() -> None:
    result = coerce_json_value([1, 2], list[int])
    assert result == [1, 2]


def test_coerce_json_value_optional_none() -> None:
    assert coerce_json_value(None, str | None) is None


def test_coerce_json_value_bool() -> None:
    assert coerce_json_value(True, bool) is True


# --- parse_dataclass_from_json ---


def test_parse_dataclass_from_json_basic() -> None:
    result = parse_dataclass_from_json(PointResult, {"x": 1, "y": 2})
    assert result.x == 1
    assert result.y == 2


def test_parse_dataclass_from_json_with_default() -> None:
    result = parse_dataclass_from_json(RequestWithOptional, {"name": "test"})
    assert result.name == "test"
    assert result.label is None


def test_parse_dataclass_from_json_from_json_dict_protocol() -> None:
    result = parse_dataclass_from_json(RequestWithFromJson, {"name": "hello"})
    assert result.name == "HELLO"


# --- serialize_to_json_dict ---


def test_serialize_to_json_dict_protocol() -> None:
    data = serialize_to_json_dict(TaggedResult(tag="v1"))
    assert data == {"tag": "v1"}


def test_serialize_to_json_dict_dataclass_fallback() -> None:
    data = serialize_to_json_dict(PointResult(x=3, y=4))
    assert data == {"x": 3, "y": 4}

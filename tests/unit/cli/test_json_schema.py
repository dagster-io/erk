"""Tests for JSON Schema generation from Click commands."""

from dataclasses import dataclass
from typing import Any

import click

from erk.cli.json_command import json_command
from erk.cli.json_schema import (
    ERROR_SCHEMA,
    build_schema_document,
    click_param_to_json_schema,
    command_input_schema,
    dataclass_to_json_schema,
    output_type_schema,
)

# -- click_param_to_json_schema tests --


def test_string_param() -> None:
    param = click.Option(["--name"], type=click.STRING)
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "string"


def test_int_param() -> None:
    param = click.Option(["--count"], type=click.INT)
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "integer"


def test_float_param() -> None:
    param = click.Option(["--rate"], type=click.FLOAT)
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "number"


def test_bool_param() -> None:
    param = click.Option(["--verbose"], type=click.BOOL)
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "boolean"


def test_flag_param() -> None:
    param = click.Option(["--dry-run"], is_flag=True)
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "boolean"


def test_path_param() -> None:
    param = click.Option(["--output"], type=click.Path())
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "string"
    assert schema["format"] == "path"


def test_choice_param() -> None:
    param = click.Option(["--level"], type=click.Choice(["debug", "info", "error"]))
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "string"
    assert schema["enum"] == ["debug", "info", "error"]


def test_param_with_help() -> None:
    param = click.Option(["--name"], type=click.STRING, help="The user name")
    schema = click_param_to_json_schema(param)
    assert schema["description"] == "The user name"


def test_variadic_argument() -> None:
    param = click.Argument(["files"], nargs=-1, type=click.STRING)
    schema = click_param_to_json_schema(param)
    assert schema["type"] == "array"
    assert schema["items"]["type"] == "string"


# -- command_input_schema tests --


def _make_schema_test_command() -> click.Command:
    """Create a Click command with various param types for schema testing."""

    @json_command(
        exclude_json_input=frozenset({"secret"}),
        required_json_input=frozenset({"name"}),
    )
    @click.command("test-schema")
    @click.option("--name", type=str, help="User name")
    @click.option("--count", type=int, default=None, help="Item count")
    @click.option("--dry-run", is_flag=True, help="Dry run mode")
    @click.option("--secret", type=str, default=None, help="Secret value")
    def test_cmd(
        *, json_mode: bool, name: str | None, count: int | None, dry_run: bool, secret: str | None
    ) -> None:
        pass

    return test_cmd


def test_input_schema_properties() -> None:
    cmd = _make_schema_test_command()
    schema = command_input_schema(cmd)
    assert "name" in schema["properties"]
    assert "count" in schema["properties"]
    assert "dry_run" in schema["properties"]


def test_input_schema_excludes_internal_params() -> None:
    cmd = _make_schema_test_command()
    schema = command_input_schema(cmd)
    assert "json_mode" not in schema["properties"]
    assert "schema_mode" not in schema["properties"]


def test_input_schema_excludes_configured_params() -> None:
    cmd = _make_schema_test_command()
    schema = command_input_schema(cmd)
    assert "secret" not in schema["properties"]


def test_input_schema_required_fields() -> None:
    cmd = _make_schema_test_command()
    schema = command_input_schema(cmd)
    assert "name" in schema["required"]


def test_input_schema_types() -> None:
    cmd = _make_schema_test_command()
    schema = command_input_schema(cmd)
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["dry_run"]["type"] == "boolean"


# -- output_type_schema tests --


def test_output_schema_with_json_schema_classmethod() -> None:
    @dataclass(frozen=True)
    class MyResult:
        value: int

        def to_json_dict(self) -> dict[str, Any]:
            return {"value": self.value}

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


# -- build_schema_document tests --


def test_build_schema_document_structure() -> None:
    @json_command
    @click.command("my-cmd")
    @click.option("--name", type=str, default=None)
    def my_cmd(*, json_mode: bool, name: str | None) -> None:
        pass

    doc = build_schema_document(my_cmd)
    assert doc["command"] == "my-cmd"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert doc["error_schema"] == ERROR_SCHEMA


def test_build_schema_document_with_output_types() -> None:
    @dataclass(frozen=True)
    class MyOutput:
        value: int

    @json_command(output_types=(MyOutput,))
    @click.command("typed-cmd")
    @click.option("--name", type=str, default=None)
    def typed_cmd(*, json_mode: bool, name: str | None) -> None:
        pass

    doc = build_schema_document(typed_cmd)
    assert "value" in doc["output_schema"]["properties"]


# -- ERROR_SCHEMA constant --


def test_error_schema_structure() -> None:
    assert ERROR_SCHEMA["type"] == "object"
    assert "success" in ERROR_SCHEMA["properties"]
    assert "error_type" in ERROR_SCHEMA["properties"]
    assert "message" in ERROR_SCHEMA["properties"]
    assert ERROR_SCHEMA["properties"]["success"]["const"] is False

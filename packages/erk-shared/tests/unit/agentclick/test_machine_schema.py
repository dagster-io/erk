"""Tests for machine-command schema generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import click

from erk_shared.agentclick.json_schema import build_schema_document, command_input_schema
from erk_shared.agentclick.machine_command import machine_command


@dataclass(frozen=True)
class SchemaRequest:
    name: str
    labels: tuple[str, ...] = field(default_factory=tuple)
    state: Literal["open", "closed"] | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class SchemaResult:
    message: str


@machine_command(request_type=SchemaRequest, output_types=(SchemaResult,))
@click.command("schema-example")
def schema_example(*, request: SchemaRequest) -> SchemaResult:
    return SchemaResult(message=request.name)


def test_command_input_schema_uses_request_contract() -> None:
    schema = command_input_schema(schema_example)

    assert schema["required"] == ["name"]
    assert schema["properties"]["labels"] == {
        "type": "array",
        "items": {"type": "string"},
        "default": [],
    }
    assert schema["properties"]["state"]["enum"] == ["open", "closed"]
    assert schema["properties"]["state"]["type"] == ["string", "null"]
    assert schema["properties"]["dry_run"] == {"type": "boolean", "default": False}


def test_build_schema_document_includes_output_and_error_shapes() -> None:
    schema_doc = build_schema_document(schema_example)

    assert schema_doc["command"] == "schema-example"
    assert schema_doc["output_schema"]["properties"]["success"] == {
        "type": "boolean",
        "const": True,
    }
    assert schema_doc["output_schema"]["properties"]["message"] == {"type": "string"}
    assert schema_doc["error_schema"]["required"] == ["success", "error_type", "message"]

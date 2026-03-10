"""Tests for @machine_command decorator."""

import json
from dataclasses import dataclass
from typing import Any

import click
from click.testing import CliRunner

from erk_shared.agentclick.errors import AgentCliError
from erk_shared.agentclick.machine_command import MachineCommandMeta, machine_command


@dataclass(frozen=True)
class SimpleRequest:
    prompt: str
    model: str | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class SimpleResult:
    value: int

    def to_json_dict(self) -> dict[str, Any]:
        return {"value": self.value}


def _make_test_command() -> click.Command:
    """Create a minimal machine command for testing."""

    @machine_command(
        request_type=SimpleRequest,
        result_types=(SimpleResult,),
        name="test_tool",
        description="A test tool",
    )
    @click.command("test-cmd")
    def test_cmd(*, request: SimpleRequest) -> SimpleResult:
        return SimpleResult(value=len(request.prompt))

    return test_cmd


def _json_input(data: dict[str, Any]) -> str:
    """Serialize data as JSON string for CliRunner input."""
    return json.dumps(data)


# -- Basic behavior tests --


def test_schema_flag_exists() -> None:
    """--schema flag is added by @machine_command."""
    cmd = _make_test_command()
    param_names = [p.name for p in cmd.params]
    assert "schema_mode" in param_names


def test_no_json_flag() -> None:
    """Machine commands do NOT have --json flag."""
    cmd = _make_test_command()
    param_names = [p.name for p in cmd.params]
    assert "json_mode" not in param_names


def test_meta_stored_on_command() -> None:
    """@machine_command stores MachineCommandMeta on the command object."""
    cmd = _make_test_command()
    meta = cmd._machine_command_meta  # type: ignore[attr-defined]
    assert isinstance(meta, MachineCommandMeta)
    assert meta.request_type is SimpleRequest
    assert meta.result_types == (SimpleResult,)
    assert meta.name == "test_tool"
    assert meta.description == "A test tool"


def test_stdin_json_parsed_to_request() -> None:
    """Stdin JSON is deserialized into request dataclass."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input=_json_input({"prompt": "hello"}))

    assert result.exit_code == 0, f"Failed: {result.output}"
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["value"] == 5  # len("hello")


def test_optional_fields_use_defaults() -> None:
    """Missing optional fields use dataclass defaults."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input=_json_input({"prompt": "test"}))

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True


def test_extra_keys_ignored() -> None:
    """Extra keys in stdin JSON are silently ignored."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input=_json_input({"prompt": "test", "unknown_key": "value"}))

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True


def test_missing_required_field_errors() -> None:
    """Missing required field produces error."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input=_json_input({}))

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "invalid_request"


def test_invalid_json_errors() -> None:
    """Invalid JSON input produces error."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input="not json")

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "invalid_json"


def test_non_object_json_errors() -> None:
    """Non-object JSON input produces error."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input="[1, 2, 3]")

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "invalid_json"


# -- Error handling tests --


def test_agent_cli_error_serialized() -> None:
    """AgentCliError is serialized as JSON error envelope."""

    @machine_command(
        request_type=SimpleRequest,
        result_types=(),
        name="error_tool",
        description="Errors out",
    )
    @click.command("error-cmd")
    def error_cmd(*, request: SimpleRequest) -> None:
        raise AgentCliError("something went wrong", error_type="cli_error")

    runner = CliRunner()
    result = runner.invoke(error_cmd, [], input=_json_input({"prompt": "test"}))

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "cli_error"
    assert data["message"] == "something went wrong"


def test_system_exit_passes_through() -> None:
    """SystemExit is not caught by the decorator."""

    @machine_command(
        request_type=SimpleRequest,
        result_types=(),
        name="exit_tool",
        description="Exits",
    )
    @click.command("exit-cmd")
    def exit_cmd(*, request: SimpleRequest) -> None:
        raise SystemExit(42)

    runner = CliRunner()
    result = runner.invoke(exit_cmd, [], input=_json_input({"prompt": "test"}))

    assert result.exit_code == 42


# -- Schema tests --


def test_schema_flag_short_circuits() -> None:
    """--schema outputs schema without executing the command."""
    call_count = 0

    @machine_command(
        request_type=SimpleRequest,
        result_types=(SimpleResult,),
        name="schema_tool",
        description="Test schema",
    )
    @click.command("schema-cmd")
    def schema_cmd(*, request: SimpleRequest) -> SimpleResult:
        nonlocal call_count
        call_count += 1
        return SimpleResult(value=0)

    runner = CliRunner()
    result = runner.invoke(schema_cmd, ["--schema"])
    assert result.exit_code == 0
    assert call_count == 0  # command was NOT executed


def test_schema_output_structure() -> None:
    """--schema outputs a valid schema document."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, ["--schema"])
    assert result.exit_code == 0

    doc = json.loads(result.output)
    assert doc["command"] == "test_tool"
    assert doc["description"] == "A test tool"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert "error_schema" in doc
    assert doc["error_schema"]["properties"]["success"]["const"] is False


def test_schema_input_from_request_dataclass() -> None:
    """Input schema is derived from request dataclass fields, not Click params."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, ["--schema"])
    doc = json.loads(result.output)

    input_schema = doc["input_schema"]
    assert "prompt" in input_schema["properties"]
    assert input_schema["properties"]["prompt"]["type"] == "string"
    assert "model" in input_schema["properties"]
    assert "dry_run" in input_schema["properties"]
    assert "prompt" in input_schema.get("required", [])


# -- Result serialization tests --


def test_result_with_to_json_dict() -> None:
    """Result with to_json_dict() is serialized via that method."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [], input=_json_input({"prompt": "hello"}))

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["value"] == 5


def test_result_plain_dataclass() -> None:
    """Plain dataclass result (no to_json_dict) uses asdict fallback."""

    @dataclass(frozen=True)
    class PlainResult:
        name: str
        count: int

    @machine_command(
        request_type=SimpleRequest,
        result_types=(PlainResult,),
        name="plain_tool",
        description="Returns plain dataclass",
    )
    @click.command("plain-cmd")
    def plain_cmd(*, request: SimpleRequest) -> PlainResult:
        return PlainResult(name="test", count=7)

    runner = CliRunner()
    result = runner.invoke(plain_cmd, [], input=_json_input({"prompt": "test"}))

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["name"] == "test"
    assert data["count"] == 7


def test_tty_stdin_uses_empty_request() -> None:
    """When stdin is a TTY, request uses defaults for all optional fields."""

    @dataclass(frozen=True)
    class AllOptionalRequest:
        name: str | None = None
        count: int = 0

    @dataclass(frozen=True)
    class EchoResult:
        name: str | None
        count: int

        def to_json_dict(self) -> dict[str, Any]:
            return {"name": self.name, "count": self.count}

    @machine_command(
        request_type=AllOptionalRequest,
        result_types=(EchoResult,),
        name="echo_tool",
        description="Echoes request",
    )
    @click.command("echo-cmd")
    def echo_cmd(*, request: AllOptionalRequest) -> EchoResult:
        return EchoResult(name=request.name, count=request.count)

    runner = CliRunner()
    # CliRunner.invoke with no input simulates a TTY
    result = runner.invoke(echo_cmd, [])

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["name"] is None
    assert data["count"] == 0

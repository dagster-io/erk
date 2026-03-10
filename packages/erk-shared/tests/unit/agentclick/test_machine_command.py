"""Tests for @machine_command decorator and supporting functions."""

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import click
from click.testing import CliRunner

from erk_shared.agentclick.dataclass_json import coerce_json_value
from erk_shared.agentclick.machine_command import (
    MachineCommandError,
    MachineCommandMeta,
    emit_machine_error,
    emit_machine_result,
    machine_command,
    parse_machine_request,
)


@dataclass(frozen=True)
class SimpleRequest:
    prompt: str
    count: int = 1


@dataclass(frozen=True)
class SimpleResult:
    answer: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"answer": self.answer}


def _make_cmd(
    request_type: type = SimpleRequest,
    output_types: tuple[type, ...] = (SimpleResult,),
) -> click.Command:
    """Create a minimal Click command decorated with @machine_command for testing."""

    @machine_command(request_type=request_type, output_types=output_types)
    @click.command("test-cmd")
    def test_cmd(*, request: SimpleRequest) -> SimpleResult:
        return SimpleResult(answer=f"echo: {request.prompt}")

    return test_cmd


def test_machine_command_stores_meta() -> None:
    """@machine_command stores MachineCommandMeta on the command object."""
    cmd = _make_cmd()
    meta = cmd._machine_command_meta  # type: ignore[attr-defined]
    assert isinstance(meta, MachineCommandMeta)
    assert meta.request_type is SimpleRequest
    assert meta.output_types == (SimpleResult,)


def test_machine_command_adds_schema_flag() -> None:
    """@machine_command adds --schema flag to the command."""
    cmd = _make_cmd()
    param_names = [p.name for p in cmd.params]
    assert "schema_mode" in param_names


def test_machine_command_schema_output() -> None:
    """--schema flag outputs JSON Schema document."""
    cmd = _make_cmd()
    runner = CliRunner()
    result = runner.invoke(cmd, ["--schema"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "input_schema" in data
    assert "output_schema" in data
    assert "error_schema" in data


def test_machine_command_success_flow() -> None:
    """Successful execution emits JSON with success=True."""
    cmd = _make_cmd()
    runner = CliRunner()
    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"prompt": "hello"},
    ):
        result = runner.invoke(cmd, [])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["answer"] == "echo: hello"


def test_machine_command_error_flow() -> None:
    """MachineCommandError result emits JSON with success=False."""

    @machine_command(request_type=SimpleRequest, output_types=(SimpleResult,))
    @click.command("err-cmd")
    def err_cmd(*, request: SimpleRequest) -> SimpleResult | MachineCommandError:
        return MachineCommandError(error_type="test_error", message="things broke")

    runner = CliRunner()
    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"prompt": "x"},
    ):
        result = runner.invoke(err_cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "test_error"


def test_machine_command_invalid_json() -> None:
    """Invalid JSON input produces structured error."""
    cmd = _make_cmd()
    runner = CliRunner()
    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        side_effect=json.JSONDecodeError("oops", "", 0),
    ):
        result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "invalid_json_input"


def test_machine_command_missing_required_field() -> None:
    """Missing required field produces structured error."""
    cmd = _make_cmd()
    runner = CliRunner()
    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={},
    ):
        result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "invalid_request"
    assert "prompt" in data["message"]


def test_machine_command_unknown_field() -> None:
    """Unknown field in request produces structured error."""
    cmd = _make_cmd()
    runner = CliRunner()
    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"prompt": "hi", "bogus": True},
    ):
        result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "invalid_request"
    assert "bogus" in data["message"]


def test_machine_command_default_field() -> None:
    """Omitted field with default uses the default value."""
    runner = CliRunner()

    @machine_command(request_type=SimpleRequest, output_types=())
    @click.command("default-cmd")
    def default_cmd(*, request: SimpleRequest) -> None:
        click.echo(json.dumps({"count": request.count}))

    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"prompt": "test"},
    ):
        result = runner.invoke(default_cmd, [])
    assert result.exit_code == 0
    # Output contains the default count of 1
    lines = result.output.strip().split("\n")
    inner_data = json.loads(lines[0])
    assert inner_data["count"] == 1


def test_parse_machine_request_happy_path() -> None:
    """parse_machine_request correctly constructs a frozen dataclass."""
    req = parse_machine_request(SimpleRequest, {"prompt": "hello", "count": 5})
    assert req.prompt == "hello"
    assert req.count == 5


def test_coerce_bool() -> None:
    """coerce_json_value validates booleans strictly."""
    assert coerce_json_value(True, bool) is True
    assert coerce_json_value(False, bool) is False


def test_coerce_optional_none() -> None:
    """coerce_json_value handles None for optional types."""
    optional_str = str | None
    result = coerce_json_value(None, optional_str)
    assert result is None


def test_emit_machine_error_output() -> None:
    """emit_machine_error writes structured JSON to stdout."""
    runner = CliRunner()

    @click.command()
    def cmd() -> None:
        emit_machine_error(MachineCommandError(error_type="oops", message="broke"))

    result = runner.invoke(cmd)
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "oops"


def test_emit_machine_result_output() -> None:
    """emit_machine_result writes structured JSON with success=True."""
    runner = CliRunner()

    @click.command()
    def cmd() -> None:
        emit_machine_result(SimpleResult(answer="ok"))

    result = runner.invoke(cmd)
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["answer"] == "ok"

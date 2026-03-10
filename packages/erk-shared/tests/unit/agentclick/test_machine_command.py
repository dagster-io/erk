"""Tests for explicit machine commands."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import click
from click.testing import CliRunner

from erk_shared.agentclick.machine_command import (
    MachineCommandError,
    machine_command,
)


@dataclass(frozen=True)
class ExampleRequest:
    name: str
    dry_run: bool = False


@dataclass(frozen=True)
class ExampleResult:
    greeting: str


@dataclass(frozen=True)
class FactoryRequest:
    name: str
    labels: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FactoryResult:
    label_count: int


def _make_command() -> click.Command:
    @machine_command(request_type=ExampleRequest, output_types=(ExampleResult,))
    @click.command("example")
    def example(*, request: ExampleRequest) -> ExampleResult:
        return ExampleResult(greeting=f"hello {request.name}")

    return example


def test_machine_command_reads_stdin_and_emits_success() -> None:
    runner = CliRunner()
    cmd = _make_command()

    result = runner.invoke(cmd, input='{"name": "alice"}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": True,
        "greeting": "hello alice",
    }


def test_machine_command_unknown_field_emits_structured_error() -> None:
    runner = CliRunner()
    cmd = _make_command()

    result = runner.invoke(cmd, input='{"name": "alice", "bogus": true}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": False,
        "error_type": "invalid_json_input",
        "message": "Unknown field: bogus",
    }


def test_machine_command_catches_click_exceptions() -> None:
    @machine_command(request_type=ExampleRequest, output_types=(ExampleResult,))
    @click.command("example")
    def failing_example(*, request: ExampleRequest) -> ExampleResult:
        raise click.ClickException(f"bad request for {request.name}")

    runner = CliRunner()
    result = runner.invoke(failing_example, input='{"name": "alice"}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": False,
        "error_type": "cli_error",
        "message": "bad request for alice",
    }


def test_machine_command_supports_explicit_error_results() -> None:
    @machine_command(request_type=ExampleRequest, output_types=(ExampleResult,))
    @click.command("example")
    def failing_example(*, request: ExampleRequest) -> ExampleResult | MachineCommandError:
        return MachineCommandError(
            error_type="custom_error",
            message=f"cannot greet {request.name}",
        )

    runner = CliRunner()
    result = runner.invoke(failing_example, input='{"name": "alice"}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": False,
        "error_type": "custom_error",
        "message": "cannot greet alice",
    }


def test_machine_command_uses_default_factory_for_missing_fields() -> None:
    @machine_command(request_type=FactoryRequest, output_types=(FactoryResult,))
    @click.command("example")
    def factory_example(*, request: FactoryRequest) -> FactoryResult:
        return FactoryResult(label_count=len(request.labels))

    runner = CliRunner()
    result = runner.invoke(factory_example, input='{"name": "alice"}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": True,
        "label_count": 0,
    }


def test_machine_command_preserves_click_exception_error_type() -> None:
    class CustomClickException(click.ClickException):
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.error_type = "custom_error"

    @machine_command(request_type=ExampleRequest, output_types=(ExampleResult,))
    @click.command("example")
    def failing_example(*, request: ExampleRequest) -> ExampleResult:
        raise CustomClickException(f"bad request for {request.name}")

    runner = CliRunner()
    result = runner.invoke(failing_example, input='{"name": "alice"}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": False,
        "error_type": "custom_error",
        "message": "bad request for alice",
    }


def test_machine_command_falls_back_for_non_string_error_type() -> None:
    class CustomClickException(click.ClickException):
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.error_type = object()

    @machine_command(request_type=ExampleRequest, output_types=(ExampleResult,))
    @click.command("example")
    def failing_example(*, request: ExampleRequest) -> ExampleResult:
        raise CustomClickException(f"bad request for {request.name}")

    runner = CliRunner()
    result = runner.invoke(failing_example, input='{"name": "alice"}')

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "success": False,
        "error_type": "cli_error",
        "message": "bad request for alice",
    }

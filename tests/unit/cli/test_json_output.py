"""Tests for the @json_output decorator and emit_json helper."""

import json

import click
from click.testing import CliRunner

from erk.cli.ensure import UserFacingCliError
from erk.cli.json_output import emit_json, json_output


def test_json_flag_added_to_command() -> None:
    """The @json_output decorator adds a --json flag to the command."""

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        if json_mode:
            emit_json({"key": "value"})

    param_names = [p.name for p in my_cmd.params]
    assert "json_mode" in param_names


def test_json_mode_emits_json() -> None:
    """When --json is passed, command can emit JSON via emit_json."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        if json_mode:
            emit_json({"key": "value"})

    result = runner.invoke(my_cmd, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["key"] == "value"


def test_no_json_flag_runs_normally() -> None:
    """Without --json, command runs with normal output."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        if json_mode:
            emit_json({"key": "value"})
            return
        click.echo("human output")

    result = runner.invoke(my_cmd, [])
    assert result.exit_code == 0
    assert result.output.strip() == "human output"


def test_json_mode_catches_user_facing_error() -> None:
    """UserFacingCliError is caught and serialized as JSON in json_mode."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        raise UserFacingCliError("something went wrong", error_type="test_error")

    result = runner.invoke(my_cmd, ["--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "test_error"
    assert data["message"] == "something went wrong"


def test_json_mode_passes_through_system_exit() -> None:
    """SystemExit passes through without JSON wrapping."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        raise SystemExit(42)

    result = runner.invoke(my_cmd, ["--json"])
    assert result.exit_code == 42


def test_user_facing_error_without_json_shows_normally() -> None:
    """Without --json, UserFacingCliError shows styled error (handled by Click)."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        raise UserFacingCliError("bad input")

    result = runner.invoke(my_cmd, [])
    assert result.exit_code == 1
    assert "bad input" in result.output


def test_emit_json_adds_success_true() -> None:
    """emit_json automatically adds success=True to the output."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        emit_json({"data": [1, 2, 3]})

    result = runner.invoke(my_cmd, ["--json"])
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"] == [1, 2, 3]


def test_default_error_type() -> None:
    """UserFacingCliError defaults to error_type='cli_error'."""
    runner = CliRunner()

    @json_output
    @click.command("test-cmd")
    def my_cmd(*, json_mode: bool) -> None:
        raise UserFacingCliError("generic error")

    result = runner.invoke(my_cmd, ["--json"])
    data = json.loads(result.output)
    assert data["error_type"] == "cli_error"

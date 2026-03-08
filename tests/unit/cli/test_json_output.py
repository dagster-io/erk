"""Tests for @json_output decorator and emit_json helper."""

import json

import click
from click.testing import CliRunner

from erk.cli.ensure import UserFacingCliError
from erk.cli.json_output import emit_json, json_output


def _make_test_command() -> click.Command:
    """Create a minimal Click command decorated with @json_output for testing."""

    @json_output
    @click.command("test-cmd")
    def test_cmd(*, json_mode: bool) -> None:
        if json_mode:
            emit_json({"key": "value"})
            return
        click.echo("human output")

    return test_cmd


def test_adds_json_flag() -> None:
    """--json appears in command params."""
    cmd = _make_test_command()
    param_names = [p.name for p in cmd.params]
    assert "json_mode" in param_names


def test_no_flag_passes_through() -> None:
    """Normal behavior without --json."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, [])
    assert result.exit_code == 0
    assert "human output" in result.output


def test_json_flag_emits_json() -> None:
    """--json causes JSON output."""
    cmd = _make_test_command()
    runner = CliRunner()
    result = runner.invoke(cmd, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["key"] == "value"


def test_catches_user_facing_error() -> None:
    """UserFacingCliError is serialized as JSON when --json is active."""

    @json_output
    @click.command("error-cmd")
    def error_cmd(*, json_mode: bool) -> None:
        raise UserFacingCliError("something went wrong", error_type="cli_error")

    runner = CliRunner()
    result = runner.invoke(error_cmd, ["--json"])
    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "cli_error"
    assert data["message"] == "something went wrong"


def test_preserves_error_type() -> None:
    """Custom error_type is preserved in JSON output."""

    @json_output
    @click.command("typed-error-cmd")
    def typed_error_cmd(*, json_mode: bool) -> None:
        raise UserFacingCliError("auth failed", error_type="auth_required")

    runner = CliRunner()
    result = runner.invoke(typed_error_cmd, ["--json"])
    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "auth_required"
    assert data["message"] == "auth failed"


def test_system_exit_passes_through() -> None:
    """SystemExit is not caught by the decorator."""

    @json_output
    @click.command("exit-cmd")
    def exit_cmd(*, json_mode: bool) -> None:
        raise SystemExit(42)

    runner = CliRunner()
    result = runner.invoke(exit_cmd, ["--json"])
    assert result.exit_code == 42


def test_error_without_json_flag_uses_normal_handling() -> None:
    """Without --json, UserFacingCliError uses Click's normal error handling."""

    @json_output
    @click.command("normal-error-cmd")
    def normal_error_cmd(*, json_mode: bool) -> None:
        raise UserFacingCliError("normal error", error_type="cli_error")

    runner = CliRunner()
    result = runner.invoke(normal_error_cmd, [])
    assert result.exit_code == 1
    # Should NOT be JSON — Click's normal error handling
    assert "normal error" in result.output
    # Verify it's not valid JSON (it's the styled Click error)
    lines = [line for line in result.output.strip().split("\n") if line.strip()]
    for line in lines:
        try:
            parsed = json.loads(line)
            # If we get valid JSON, it should not have our success key
            assert "success" not in parsed
        except json.JSONDecodeError:
            pass  # Expected: not JSON

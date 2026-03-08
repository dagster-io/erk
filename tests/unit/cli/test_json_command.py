"""Tests for @json_command decorator, emit_json, and emit_json_result."""

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import click
from click.testing import CliRunner

from erk.cli.ensure import UserFacingCliError
from erk.cli.json_command import emit_json, emit_json_result, json_command


# -- Helpers --


def _make_test_command() -> click.Command:
    """Create a minimal Click command decorated with @json_command for testing."""

    @json_command
    @click.command("test-cmd")
    def test_cmd(*, json_mode: bool) -> None:
        if json_mode:
            emit_json({"key": "value"})
            return
        click.echo("human output")

    return test_cmd


def _patch_stdin_json(data: dict[str, Any] | None = None) -> Any:
    """Patch read_stdin_json to return given data (or None for TTY)."""
    return patch("erk.cli.json_command.read_stdin_json", return_value=data)


# -- Existing tests (ported from test_json_output.py) --


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

    @json_command
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

    @json_command
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

    @json_command
    @click.command("exit-cmd")
    def exit_cmd(*, json_mode: bool) -> None:
        raise SystemExit(42)

    runner = CliRunner()
    result = runner.invoke(exit_cmd, ["--json"])
    assert result.exit_code == 42


def test_error_without_json_flag_uses_normal_handling() -> None:
    """Without --json, UserFacingCliError uses Click's normal error handling."""

    @json_command
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


# -- JSON input tests --


def test_json_input_from_stdin() -> None:
    """Piped JSON populates kwargs when --json is active."""

    @json_command
    @click.command("input-cmd")
    @click.option("--name", default=None)
    @click.option("--count", type=int, default=None)
    def input_cmd(*, json_mode: bool, name: str | None, count: int | None) -> None:
        if json_mode:
            emit_json({"name": name, "count": count})
            return
        click.echo(f"name={name} count={count}")

    runner = CliRunner()
    with _patch_stdin_json({"name": "alice", "count": 5}):
        result = runner.invoke(input_cmd, ["--json"])

    assert result.exit_code == 0, f"Failed: {result.output}"
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["name"] == "alice"
    assert data["count"] == 5


def test_json_input_unknown_keys_error() -> None:
    """Unknown keys produce JSON error."""

    @json_command
    @click.command("input-cmd")
    @click.option("--name", default=None)
    def input_cmd(*, json_mode: bool, name: str | None) -> None:
        emit_json({"name": name})

    runner = CliRunner()
    with _patch_stdin_json({"name": "alice", "bogus": True}):
        result = runner.invoke(input_cmd, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "invalid_json_input"
    assert "bogus" in data["message"]


def test_json_input_skipped_when_tty() -> None:
    """No stdin read when interactive (TTY) — read_stdin_json returns None."""

    @json_command
    @click.command("input-cmd")
    @click.option("--name", default=None)
    def input_cmd(*, json_mode: bool, name: str | None) -> None:
        emit_json({"name": name})

    runner = CliRunner()
    with _patch_stdin_json(None):
        result = runner.invoke(input_cmd, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["name"] is None


def test_exclude_json_input() -> None:
    """Excluded params are not mapped from JSON input."""

    @json_command(exclude_json_input=frozenset({"secret"}))
    @click.command("excl-cmd")
    @click.option("--name", default=None)
    @click.option("--secret", default=None)
    def excl_cmd(*, json_mode: bool, name: str | None, secret: str | None) -> None:
        emit_json({"name": name, "secret": secret})

    runner = CliRunner()
    with _patch_stdin_json({"name": "alice", "secret": "should-fail"}):
        result = runner.invoke(excl_cmd, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["error_type"] == "invalid_json_input"
    assert "secret" in data["message"]


def test_required_json_input_missing() -> None:
    """Missing required field produces JSON error."""

    @json_command(required_json_input=frozenset({"prompt"}))
    @click.command("req-cmd")
    @click.option("--prompt", default=None)
    def req_cmd(*, json_mode: bool, prompt: str | None) -> None:
        emit_json({"prompt": prompt})

    runner = CliRunner()
    with _patch_stdin_json(None):
        result = runner.invoke(req_cmd, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["success"] is False
    assert data["error_type"] == "invalid_json_input"
    assert "prompt" in data["message"]


def test_required_json_input_present() -> None:
    """Present required field passes through."""

    @json_command(required_json_input=frozenset({"prompt"}))
    @click.command("req-cmd")
    @click.option("--prompt", default=None)
    def req_cmd(*, json_mode: bool, prompt: str | None) -> None:
        emit_json({"prompt": prompt})

    runner = CliRunner()
    with _patch_stdin_json({"prompt": "hello"}):
        result = runner.invoke(req_cmd, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["prompt"] == "hello"


# -- emit_json_result tests --


def test_emit_json_result_with_to_json_dict() -> None:
    """Protocol method to_json_dict() is used when available."""

    @dataclass(frozen=True)
    class MyResult:
        value: int

        def to_json_dict(self) -> dict[str, Any]:
            return {"custom": self.value * 2}

    @json_command
    @click.command("result-cmd")
    def result_cmd(*, json_mode: bool) -> None:
        emit_json_result(MyResult(value=21))

    runner = CliRunner()
    result = runner.invoke(result_cmd, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["custom"] == 42


def test_return_value_auto_serialized_in_json_mode() -> None:
    """Command return value is auto-serialized as JSON when --json is active."""

    @dataclass(frozen=True)
    class AutoResult:
        value: int

        def to_json_dict(self) -> dict[str, Any]:
            return {"doubled": self.value * 2}

    @json_command
    @click.command("auto-cmd")
    def auto_cmd(*, json_mode: bool) -> AutoResult:
        return AutoResult(value=21)

    runner = CliRunner()
    result = runner.invoke(auto_cmd, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["doubled"] == 42


def test_return_none_no_output_in_json_mode() -> None:
    """Returning None in JSON mode emits no JSON (prevents double-output)."""

    @json_command
    @click.command("none-cmd")
    def none_cmd(*, json_mode: bool) -> None:
        # Command that handles JSON inline and returns None
        pass

    runner = CliRunner()
    result = runner.invoke(none_cmd, ["--json"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_return_value_ignored_in_non_json_mode() -> None:
    """Return value is not serialized when --json is not passed."""

    @dataclass(frozen=True)
    class IgnoredResult:
        value: int

        def to_json_dict(self) -> dict[str, Any]:
            return {"value": self.value}

    @json_command
    @click.command("ignored-cmd")
    def ignored_cmd(*, json_mode: bool) -> IgnoredResult:
        click.echo("human output")
        return IgnoredResult(value=99)

    runner = CliRunner()
    result = runner.invoke(ignored_cmd, [])
    assert result.exit_code == 0
    assert "human output" in result.output
    # Should not contain JSON
    for line in result.output.strip().split("\n"):
        try:
            parsed = json.loads(line)
            assert "success" not in parsed
        except json.JSONDecodeError:
            pass


def test_emit_json_result_with_plain_dataclass() -> None:
    """Plain dataclass uses asdict fallback."""

    @dataclass(frozen=True)
    class PlainResult:
        name: str
        count: int

    @json_command
    @click.command("plain-cmd")
    def plain_cmd(*, json_mode: bool) -> None:
        emit_json_result(PlainResult(name="test", count=7))

    runner = CliRunner()
    result = runner.invoke(plain_cmd, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip())
    assert data["success"] is True
    assert data["name"] == "test"
    assert data["count"] == 7

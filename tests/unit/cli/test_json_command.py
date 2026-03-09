"""Tests for @json_command decorator, emit_json, emit_json_result, and --schema flag."""

import json
import types
import typing
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import click
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.ensure import UserFacingCliError
from erk.cli.json_command import JsonCommandMeta, emit_json, emit_json_result, json_command

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


# -- JsonCommandMeta tests --


def test_json_command_meta_stored_on_command() -> None:
    """@json_command stores JsonCommandMeta on the command object."""

    @json_command(
        exclude_json_input=frozenset({"secret"}),
        required_json_input=frozenset({"name"}),
    )
    @click.command("meta-cmd")
    @click.option("--name", default=None)
    @click.option("--secret", default=None)
    def meta_cmd(*, json_mode: bool, name: str | None, secret: str | None) -> None:
        pass

    meta = meta_cmd._json_command_meta  # type: ignore[attr-defined]
    assert isinstance(meta, JsonCommandMeta)
    assert meta.exclude_json_input == frozenset({"secret"})
    assert meta.required_json_input == frozenset({"name"})
    assert meta.output_types == ()


def test_json_command_meta_with_output_types() -> None:
    """output_types parameter is stored in JsonCommandMeta."""

    @dataclass(frozen=True)
    class ResultA:
        value: int

    @json_command(output_types=(ResultA,))
    @click.command("typed-cmd")
    def typed_cmd(*, json_mode: bool) -> None:
        pass

    meta = typed_cmd._json_command_meta  # type: ignore[attr-defined]
    assert meta.output_types == (ResultA,)


# -- --schema flag tests --


def test_schema_flag_exists() -> None:
    """--schema flag is added by @json_command."""
    cmd = _make_test_command()
    param_names = [p.name for p in cmd.params]
    assert "schema_mode" in param_names


def test_schema_flag_short_circuits() -> None:
    """--schema outputs schema without executing the command."""
    call_count = 0

    @json_command
    @click.command("schema-cmd")
    @click.option("--name", type=str, default=None)
    def schema_cmd(*, json_mode: bool, name: str | None) -> None:
        nonlocal call_count
        call_count += 1

    runner = CliRunner()
    result = runner.invoke(schema_cmd, ["--schema"])
    assert result.exit_code == 0
    assert call_count == 0  # command was NOT executed


def test_schema_output_structure() -> None:
    """--schema outputs a valid schema document with input/output/error schemas."""

    @json_command
    @click.command("struct-cmd")
    @click.option("--name", type=str, default=None, help="The name")
    def struct_cmd(*, json_mode: bool, name: str | None) -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(struct_cmd, ["--schema"])
    assert result.exit_code == 0

    doc = json.loads(result.output)
    assert doc["command"] == "struct-cmd"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert "error_schema" in doc
    assert doc["error_schema"]["properties"]["success"]["const"] is False


def test_schema_includes_input_params() -> None:
    """--schema output includes command parameters in input_schema."""

    @json_command
    @click.command("params-cmd")
    @click.option("--name", type=str, default=None, help="User name")
    @click.option("--count", type=int, default=None, help="Item count")
    def params_cmd(*, json_mode: bool, name: str | None, count: int | None) -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(params_cmd, ["--schema"])
    doc = json.loads(result.output)

    assert "name" in doc["input_schema"]["properties"]
    assert doc["input_schema"]["properties"]["name"]["type"] == "string"
    assert doc["input_schema"]["properties"]["count"]["type"] == "integer"


def test_schema_with_output_types() -> None:
    """--schema output includes output_schema from registered types."""

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

    @json_command(output_types=(MyResult,))
    @click.command("typed-schema-cmd")
    def typed_cmd(*, json_mode: bool) -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(typed_cmd, ["--schema"])
    doc = json.loads(result.output)

    assert "value" in doc["output_schema"]["properties"]


# -- output_types validation test --


def test_output_types_matches_return_annotation() -> None:
    """Every @json_command's output_types must match its return annotation."""

    def _collect_json_commands(group: click.BaseCommand) -> list[click.BaseCommand]:
        """Recursively collect all commands with _json_command_meta."""
        result = []
        if hasattr(group, "_json_command_meta"):
            result.append(group)
        if isinstance(group, click.Group):
            for cmd in group.commands.values():
                result.extend(_collect_json_commands(cmd))
        return result

    def _unwrap_return_types(annotation: Any) -> set[type]:
        """Decompose A | B unions into member types."""
        origin = typing.get_origin(annotation)
        if origin is typing.Union or isinstance(annotation, types.UnionType):
            return set(typing.get_args(annotation))
        return {annotation}

    commands = _collect_json_commands(cli)
    assert len(commands) > 0, "No @json_command commands found — check CLI import"

    failures = []
    for cmd in commands:
        meta = cmd._json_command_meta  # type: ignore[attr-defined]
        original_callback = cmd._json_command_original_callback  # type: ignore[attr-defined]
        if original_callback is None:
            continue

        hints = typing.get_type_hints(original_callback)
        return_annotation = hints.get("return", type(None))

        if return_annotation is type(None):
            # -> None means output_types must be ()
            if meta.output_types != ():
                failures.append(f"{cmd.name}: return None but output_types={meta.output_types!r}")
        else:
            return_types = _unwrap_return_types(return_annotation)
            declared_types = set(meta.output_types)
            if return_types != declared_types:
                failures.append(
                    f"{cmd.name}: return annotation types {return_types}"
                    f" != output_types {declared_types}"
                )

    assert not failures, "output_types mismatch:\n" + "\n".join(failures)

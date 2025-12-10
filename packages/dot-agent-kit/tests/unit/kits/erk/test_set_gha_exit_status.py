"""Unit tests for set_gha_exit_status kit CLI command.

Tests running commands and capturing exit status for GitHub Actions.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.scripts.erk.set_gha_exit_status import (
    CommandRunner,
    ExitStatusSuccess,
    _set_gha_exit_status_impl,
    _write_to_github_output,
)
from dot_agent_kit.data.kits.erk.scripts.erk.set_gha_exit_status import (
    set_gha_exit_status as set_gha_exit_status_command,
)


class FakeCommandRunner(CommandRunner):
    """Fake command runner for testing."""

    def __init__(self, exit_code: int = 0) -> None:
        self._exit_code = exit_code
        self.commands: list[tuple[list[str], Path]] = []

    def run(self, command: list[str], cwd: Path) -> int:
        self.commands.append((command, cwd))
        return self._exit_code


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    cwd: Path
    command_runner: CommandRunner


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_captures_success_exit_code(tmp_path: Path) -> None:
    """Test that exit code 0 is captured as success."""
    runner = FakeCommandRunner(exit_code=0)

    result = _set_gha_exit_status_impl(runner, tmp_path, "impl_success", ("make", "test"))

    assert isinstance(result, ExitStatusSuccess)
    assert result.success is True
    assert result.exit_code == 0
    assert result.output_var == "impl_success"
    assert result.output_value is True


def test_impl_captures_failure_exit_code(tmp_path: Path) -> None:
    """Test that non-zero exit code is captured as failure."""
    runner = FakeCommandRunner(exit_code=1)

    result = _set_gha_exit_status_impl(runner, tmp_path, "impl_success", ("false",))

    assert result.exit_code == 1
    assert result.output_value is False


def test_impl_passes_command_to_runner(tmp_path: Path) -> None:
    """Test that command is passed to runner correctly."""
    runner = FakeCommandRunner(exit_code=0)

    _set_gha_exit_status_impl(runner, tmp_path, "result", ("echo", "hello", "world"))

    assert len(runner.commands) == 1
    command, cwd = runner.commands[0]
    assert command == ["echo", "hello", "world"]
    assert cwd == tmp_path


def test_impl_writes_to_github_output(tmp_path: Path, monkeypatch: object) -> None:
    """Test that results are written to GITHUB_OUTPUT."""
    runner = FakeCommandRunner(exit_code=0)
    output_file = tmp_path / "github_output.txt"

    # Use pytest's monkeypatch fixture via the monkeypatch parameter
    import pytest

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    _set_gha_exit_status_impl(runner, tmp_path, "test_var", ("true",))

    content = output_file.read_text(encoding="utf-8")
    assert "exit_code=0" in content
    assert "test_var=true" in content

    monkeypatch.undo()


# ============================================================================
# 2. write_to_github_output Tests (2 tests)
# ============================================================================


def test_write_to_github_output_writes_file(tmp_path: Path) -> None:
    """Test that _write_to_github_output writes to file."""
    output_file = tmp_path / "output.txt"
    old_env = os.environ.get("GITHUB_OUTPUT")
    try:
        os.environ["GITHUB_OUTPUT"] = str(output_file)
        result = _write_to_github_output("key", "value")
        assert result is True
        assert output_file.read_text(encoding="utf-8") == "key=value\n"
    finally:
        if old_env is None:
            os.environ.pop("GITHUB_OUTPUT", None)
        else:
            os.environ["GITHUB_OUTPUT"] = old_env


def test_write_to_github_output_returns_false_when_not_set(tmp_path: Path) -> None:
    """Test that _write_to_github_output returns False when env var not set."""
    old_env = os.environ.get("GITHUB_OUTPUT")
    try:
        os.environ.pop("GITHUB_OUTPUT", None)
        result = _write_to_github_output("key", "value")
        assert result is False
    finally:
        if old_env is not None:
            os.environ["GITHUB_OUTPUT"] = old_env


# ============================================================================
# 3. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_captures_success(tmp_path: Path) -> None:
    """Test CLI captures successful command."""
    runner = CliRunner()
    cmd_runner = FakeCommandRunner(exit_code=0)
    ctx = CLIContext(cwd=tmp_path, command_runner=cmd_runner)

    result = runner.invoke(
        set_gha_exit_status_command,
        ["--output-var", "impl_success", "echo", "hello"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["exit_code"] == 0
    assert output["output_value"] is True


def test_cli_captures_failure(tmp_path: Path) -> None:
    """Test CLI captures failed command."""
    runner = CliRunner()
    cmd_runner = FakeCommandRunner(exit_code=1)
    ctx = CLIContext(cwd=tmp_path, command_runner=cmd_runner)

    result = runner.invoke(
        set_gha_exit_status_command,
        ["--output-var", "impl_success", "false"],
        obj=ctx,
    )

    # CLI should exit 0 even if inner command failed
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["exit_code"] == 1
    assert output["output_value"] is False


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    cmd_runner = FakeCommandRunner(exit_code=0)
    ctx = CLIContext(cwd=tmp_path, command_runner=cmd_runner)

    result = runner.invoke(
        set_gha_exit_status_command,
        ["--output-var", "test", "echo", "test"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "exit_code" in output
    assert "output_var" in output
    assert "output_value" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["exit_code"], int)
    assert isinstance(output["output_var"], str)
    assert isinstance(output["output_value"], bool)

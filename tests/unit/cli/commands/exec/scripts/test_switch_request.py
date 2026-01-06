"""Tests for switch-request exec command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.switch_request import switch_request


def test_switch_request_creates_marker_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """switch-request creates ~/.erk/switch-request marker file."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Create .erk directory
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(switch_request, ["123"])

    assert result.exit_code == 0
    assert (erk_dir / "switch-request").exists()
    assert (erk_dir / "switch-request").read_text(encoding="utf-8") == "123"


def test_switch_request_creates_erk_directory_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """switch-request creates ~/.erk/ directory if it doesn't exist."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Don't create .erk directory - command should create it
    erk_dir = tmp_path / ".erk"
    assert not erk_dir.exists()

    runner = CliRunner()
    result = runner.invoke(switch_request, ["456"])

    assert result.exit_code == 0
    assert erk_dir.exists()
    assert (erk_dir / "switch-request").exists()


def test_switch_request_with_command_creates_command_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """switch-request with --command creates switch-request-command file."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(switch_request, ["789", "--command", "/erk:plan-implement"])

    assert result.exit_code == 0
    assert (erk_dir / "switch-request").read_text(encoding="utf-8") == "789"
    assert (erk_dir / "switch-request-command").exists()
    assert (erk_dir / "switch-request-command").read_text(encoding="utf-8") == "/erk:plan-implement"


def test_switch_request_without_command_removes_stale_command_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """switch-request without --command removes any existing command file."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    # Create a stale command file
    command_file = erk_dir / "switch-request-command"
    command_file.write_text("old-command", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(switch_request, ["123"])

    assert result.exit_code == 0
    assert not command_file.exists()


def test_switch_request_outputs_json_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """switch-request outputs JSON success message."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(switch_request, ["123"])

    assert result.exit_code == 0
    assert '"success": true' in result.output
    assert "123" in result.output

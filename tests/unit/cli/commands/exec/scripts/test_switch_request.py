"""Tests for switch-request exec command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.switch_request import switch_request
from erk_shared.context.context import ErkContext
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation


def test_switch_request_creates_marker_file(tmp_path: Path) -> None:
    """switch-request creates switch-request marker file."""
    erk_dir = tmp_path / "erk"
    erk_dir.mkdir()

    installation = FakeErkInstallation(root_path=erk_dir)
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path, erk_installation=installation)

    runner = CliRunner()
    result = runner.invoke(switch_request, ["123"], obj=ctx)

    assert result.exit_code == 0
    assert (erk_dir / "switch-request").exists()
    assert (erk_dir / "switch-request").read_text(encoding="utf-8") == "123"


def test_switch_request_creates_erk_directory_if_missing(tmp_path: Path) -> None:
    """switch-request creates erk directory if it doesn't exist."""
    erk_dir = tmp_path / "erk"
    # Don't create the directory - command should create it
    assert not erk_dir.exists()

    installation = FakeErkInstallation(root_path=erk_dir)
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path, erk_installation=installation)

    runner = CliRunner()
    result = runner.invoke(switch_request, ["456"], obj=ctx)

    assert result.exit_code == 0
    assert erk_dir.exists()
    assert (erk_dir / "switch-request").exists()


def test_switch_request_with_command_creates_command_file(tmp_path: Path) -> None:
    """switch-request with --command creates switch-request-command file."""
    erk_dir = tmp_path / "erk"
    erk_dir.mkdir()

    installation = FakeErkInstallation(root_path=erk_dir)
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path, erk_installation=installation)

    runner = CliRunner()
    result = runner.invoke(switch_request, ["789", "--command", "/erk:plan-implement"], obj=ctx)

    assert result.exit_code == 0
    assert (erk_dir / "switch-request").read_text(encoding="utf-8") == "789"
    assert (erk_dir / "switch-request-command").exists()
    assert (erk_dir / "switch-request-command").read_text(encoding="utf-8") == "/erk:plan-implement"


def test_switch_request_without_command_removes_stale_command_file(tmp_path: Path) -> None:
    """switch-request without --command removes any existing command file."""
    erk_dir = tmp_path / "erk"
    erk_dir.mkdir()

    # Create a stale command file
    command_file = erk_dir / "switch-request-command"
    command_file.write_text("old-command", encoding="utf-8")

    installation = FakeErkInstallation(root_path=erk_dir)
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path, erk_installation=installation)

    runner = CliRunner()
    result = runner.invoke(switch_request, ["123"], obj=ctx)

    assert result.exit_code == 0
    assert not command_file.exists()


def test_switch_request_outputs_json_success(tmp_path: Path) -> None:
    """switch-request outputs JSON success message."""
    erk_dir = tmp_path / "erk"
    erk_dir.mkdir()

    installation = FakeErkInstallation(root_path=erk_dir)
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path, erk_installation=installation)

    runner = CliRunner()
    result = runner.invoke(switch_request, ["123"], obj=ctx)

    assert result.exit_code == 0
    assert '"success": true' in result.output
    assert "123" in result.output

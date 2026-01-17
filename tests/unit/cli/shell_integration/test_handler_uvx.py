"""Tests for uvx warning in shell integration handler."""

from pathlib import Path
from unittest.mock import patch

from erk.cli.shell_integration.handler import (
    HandlerDependencies,
    _invoke_hidden_command,
)
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation


def _create_deps(
    *,
    shell_integration: bool,
    is_uvx: bool,
    confirm_responses: list[bool] | None,
) -> HandlerDependencies:
    """Create HandlerDependencies with specified configuration."""
    config = GlobalConfig.test(Path("/fake/erk"), shell_integration=shell_integration)
    return HandlerDependencies(
        erk_installation=FakeErkInstallation(config=config),
        console=FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=confirm_responses,
        ),
        is_uvx=is_uvx,
    )


def test_handler_warns_for_shell_integration_commands_via_uvx(capsys) -> None:
    """Warning is displayed for shell integration commands invoked via uvx."""
    deps = _create_deps(
        shell_integration=True,
        is_uvx=True,
        confirm_responses=[True],
    )

    with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        _invoke_hidden_command("wt checkout", ("feature-branch",), deps=deps)

    captured = capsys.readouterr()
    # Warning goes to stderr (user_output routes to stderr for shell integration)
    assert "Warning:" in captured.err
    assert "erk wt checkout" in captured.err  # Command name should be in message
    assert "shell integration" in captured.err.lower()


def test_handler_includes_command_name_in_warning(capsys) -> None:
    """Warning message includes the specific command being invoked."""
    deps = _create_deps(
        shell_integration=True,
        is_uvx=True,
        confirm_responses=[True],
    )

    with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        _invoke_hidden_command("up", (), deps=deps)

    captured = capsys.readouterr()
    assert "erk up" in captured.err


def test_handler_aborts_when_user_declines_confirmation() -> None:
    """Handler returns exit code 1 when user declines confirmation."""
    deps = _create_deps(
        shell_integration=True,
        is_uvx=True,
        confirm_responses=[False],
    )

    result = _invoke_hidden_command("wt checkout", ("feature-branch",), deps=deps)

    # Should return non-zero exit code when user declines
    assert result.passthrough is False
    assert result.exit_code == 1
    assert result.script is None


def test_handler_continues_when_user_confirms() -> None:
    """Handler proceeds with command when user confirms."""
    deps = _create_deps(
        shell_integration=True,
        is_uvx=True,
        confirm_responses=[True],
    )

    with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "/tmp/script.sh"

        _invoke_hidden_command("wt checkout", ("feature-branch",), deps=deps)

    # subprocess.run should have been called
    mock_run.assert_called_once()


def test_handler_no_warning_for_regular_venv(capsys) -> None:
    """No warning is displayed when not running via uvx."""
    deps = _create_deps(
        shell_integration=True,
        is_uvx=False,
        confirm_responses=None,
    )

    with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        _invoke_hidden_command("wt checkout", ("feature-branch",), deps=deps)

    captured = capsys.readouterr()
    # Should NOT contain the uvx warning
    assert "uvx" not in captured.err.lower()


def test_handler_no_warning_for_non_shell_integration_commands() -> None:
    """No warning for commands that aren't shell integration commands."""
    # For non-shell-integration commands, deps is not used, so we don't need to inject
    # The function returns passthrough=True before checking deps
    result = _invoke_hidden_command("status", ())

    # Should return passthrough=True for unknown commands
    assert result.passthrough is True


def test_handler_no_warning_for_help_flags() -> None:
    """No warning when help flag is passed (passthrough mode)."""
    # For help flags, the function returns early before checking deps
    result = _invoke_hidden_command("wt checkout", ("--help",))

    # Should return passthrough=True for help
    assert result.passthrough is True

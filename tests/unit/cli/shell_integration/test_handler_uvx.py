"""Tests for uvx warning in shell integration handler."""

from unittest.mock import patch

from erk.cli.shell_integration.handler import _invoke_hidden_command


def test_handler_warns_for_shell_integration_commands_via_uvx(capsys) -> None:
    """Warning is displayed for shell integration commands invoked via uvx."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        with patch("erk.cli.shell_integration.handler.click.confirm", return_value=True):
            with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = ""

                _invoke_hidden_command("checkout", ("feature-branch",))

    captured = capsys.readouterr()
    # Warning goes to stderr (user_output routes to stderr for shell integration)
    assert "Warning:" in captured.err
    assert "erk checkout" in captured.err  # Command name should be in message
    assert "shell integration" in captured.err.lower()


def test_handler_includes_command_name_in_warning(capsys) -> None:
    """Warning message includes the specific command being invoked."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        with patch("erk.cli.shell_integration.handler.click.confirm", return_value=True):
            with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = ""

                _invoke_hidden_command("up", ())

    captured = capsys.readouterr()
    assert "erk up" in captured.err


def test_handler_aborts_when_user_declines_confirmation() -> None:
    """Handler returns exit code 1 when user declines confirmation."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        with patch("erk.cli.shell_integration.handler.click.confirm", return_value=False):
            result = _invoke_hidden_command("checkout", ("feature-branch",))

    # Should return non-zero exit code when user declines
    assert result.passthrough is False
    assert result.exit_code == 1
    assert result.script is None


def test_handler_continues_when_user_confirms() -> None:
    """Handler proceeds with command when user confirms."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        with patch("erk.cli.shell_integration.handler.click.confirm", return_value=True):
            with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "/tmp/script.sh"

                _invoke_hidden_command("checkout", ("feature-branch",))

    # subprocess.run should have been called
    mock_run.assert_called_once()


def test_handler_no_warning_for_regular_venv(capsys) -> None:
    """No warning is displayed when not running via uvx."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=False):
        with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            _invoke_hidden_command("checkout", ("feature-branch",))

    captured = capsys.readouterr()
    # Should NOT contain the uvx warning
    assert "uvx" not in captured.err.lower()


def test_handler_no_warning_for_non_shell_integration_commands() -> None:
    """No warning for commands that aren't shell integration commands."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        result = _invoke_hidden_command("status", ())

    # Should return passthrough=True for unknown commands
    assert result.passthrough is True


def test_handler_no_warning_for_help_flags() -> None:
    """No warning when help flag is passed (passthrough mode)."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        result = _invoke_hidden_command("checkout", ("--help",))

    # Should return passthrough=True for help
    assert result.passthrough is True

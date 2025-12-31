"""Tests for uvx warning in shell integration handler."""

from unittest.mock import patch

from erk.cli.shell_integration.handler import _invoke_hidden_command


def test_handler_warns_for_shell_integration_commands_via_uvx(capsys) -> None:
    """Warning is displayed for shell integration commands invoked via uvx."""
    # Patch is_running_via_uvx to return True
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        # Also patch subprocess.run to avoid actual command execution
        with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            # Invoke a shell integration command
            _invoke_hidden_command("checkout", ("feature-branch",))

    captured = capsys.readouterr()
    # Warning goes to stderr (user_output routes to stderr for shell integration)
    assert "Warning:" in captured.err
    assert "uvx" in captured.err.lower() or "uv" in captured.err
    assert "shell integration" in captured.err.lower()


def test_handler_no_warning_for_regular_venv(capsys) -> None:
    """No warning is displayed when not running via uvx."""
    # Patch is_running_via_uvx to return False
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=False):
        # Also patch subprocess.run to avoid actual command execution
        with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            # Invoke a shell integration command
            _invoke_hidden_command("checkout", ("feature-branch",))

    captured = capsys.readouterr()
    # Should NOT contain the uvx warning (check stderr since user_output goes there)
    assert "Running via 'uvx erk'" not in captured.err


def test_handler_no_warning_for_non_shell_integration_commands() -> None:
    """No warning for commands that aren't shell integration commands."""
    # Patch is_running_via_uvx to return True
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        # A non-shell-integration command should pass through without warning
        result = _invoke_hidden_command("status", ())

    # Should return passthrough=True for unknown commands
    assert result.passthrough is True


def test_handler_no_warning_for_help_flags() -> None:
    """No warning when help flag is passed (passthrough mode)."""
    with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=True):
        # Help flag should trigger passthrough
        result = _invoke_hidden_command("checkout", ("--help",))

    # Should return passthrough=True for help
    assert result.passthrough is True

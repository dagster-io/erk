"""Tests for shell integration config-based behavior."""

from unittest.mock import patch

from erk.cli.shell_integration.handler import (
    ShellIntegrationResult,
    _invoke_hidden_command,
    _is_shell_integration_enabled,
)


def test_is_shell_integration_enabled_returns_false_when_config_not_exists() -> None:
    """Returns False when config file doesn't exist."""
    # Patch at the source module where RealErkInstallation is defined
    with patch(
        "erk_shared.gateway.erk_installation.real.RealErkInstallation"
    ) as mock_installation_class:
        mock_installation = mock_installation_class.return_value
        mock_installation.config_exists.return_value = False

        result = _is_shell_integration_enabled()

    assert result is False


def test_is_shell_integration_enabled_returns_false_when_config_disabled() -> None:
    """Returns False when shell_integration is False in config."""
    with patch(
        "erk_shared.gateway.erk_installation.real.RealErkInstallation"
    ) as mock_installation_class:
        mock_installation = mock_installation_class.return_value
        mock_installation.config_exists.return_value = True
        mock_config = mock_installation.load_config.return_value
        mock_config.shell_integration = False

        result = _is_shell_integration_enabled()

    assert result is False


def test_is_shell_integration_enabled_returns_true_when_config_enabled() -> None:
    """Returns True when shell_integration is True in config."""
    with patch(
        "erk_shared.gateway.erk_installation.real.RealErkInstallation"
    ) as mock_installation_class:
        mock_installation = mock_installation_class.return_value
        mock_installation.config_exists.return_value = True
        mock_config = mock_installation.load_config.return_value
        mock_config.shell_integration = True

        result = _is_shell_integration_enabled()

    assert result is True


def test_handler_passthroughs_when_shell_integration_disabled() -> None:
    """Handler returns passthrough when shell_integration is disabled (default)."""
    with patch(
        "erk.cli.shell_integration.handler._is_shell_integration_enabled", return_value=False
    ):
        # Use 'wt checkout' which IS in SHELL_INTEGRATION_COMMANDS
        result = _invoke_hidden_command("wt checkout", ("feature-branch",))

    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_handler_passthroughs_when_shell_integration_disabled_for_wt_checkout() -> None:
    """Handler returns passthrough for wt checkout when disabled."""
    with patch(
        "erk.cli.shell_integration.handler._is_shell_integration_enabled", return_value=False
    ):
        result = _invoke_hidden_command("wt checkout", ("feature-branch",))

    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_handler_passthroughs_when_shell_integration_disabled_for_up() -> None:
    """Handler returns passthrough for up command when disabled."""
    with patch(
        "erk.cli.shell_integration.handler._is_shell_integration_enabled", return_value=False
    ):
        result = _invoke_hidden_command("up", ())

    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_handler_proceeds_when_shell_integration_enabled() -> None:
    """Handler proceeds with shell integration when enabled."""
    with patch(
        "erk.cli.shell_integration.handler._is_shell_integration_enabled", return_value=True
    ):
        with patch("erk.cli.shell_integration.handler.is_running_via_uvx", return_value=False):
            with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "/tmp/script.sh"

                result = _invoke_hidden_command("up", ())

    # subprocess.run should have been called
    mock_run.assert_called_once()
    # Result should NOT be passthrough since shell integration is enabled
    assert result.passthrough is False


def test_deprecated_checkout_alias_passthroughs() -> None:
    """Deprecated top-level 'checkout' alias passthroughs to CLI.

    The top-level 'checkout' command was removed from SHELL_INTEGRATION_COMMANDS
    because it never worked without shell integration anyway.
    """
    # Should passthrough regardless of shell_integration config setting
    result = _invoke_hidden_command("checkout", ("feature-branch",))
    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_deprecated_co_alias_passthroughs() -> None:
    """Deprecated top-level 'co' alias passthroughs to CLI."""
    result = _invoke_hidden_command("co", ("feature-branch",))
    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

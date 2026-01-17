"""Tests for shell integration config-based behavior."""

from pathlib import Path
from unittest.mock import patch

from erk.cli.shell_integration.handler import (
    HandlerDependencies,
    ShellIntegrationResult,
    _invoke_hidden_command,
    _is_shell_integration_enabled,
)
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation


def _create_deps(
    *,
    config: GlobalConfig | None,
    is_uvx: bool,
) -> HandlerDependencies:
    """Create HandlerDependencies with specified configuration.

    Args:
        config: GlobalConfig to use. If None, simulates config doesn't exist.
        is_uvx: Whether to simulate running via uvx.
    """
    return HandlerDependencies(
        erk_installation=FakeErkInstallation(config=config),
        console=FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        ),
        is_uvx=is_uvx,
    )


def test_is_shell_integration_enabled_returns_false_when_config_not_exists() -> None:
    """Returns False when config file doesn't exist."""
    erk_installation = FakeErkInstallation(config=None)

    result = _is_shell_integration_enabled(erk_installation)

    assert result is False


def test_is_shell_integration_enabled_returns_false_when_config_disabled() -> None:
    """Returns False when shell_integration is False in config."""
    config = GlobalConfig.test(Path("/fake/erk"), shell_integration=False)
    erk_installation = FakeErkInstallation(config=config)

    result = _is_shell_integration_enabled(erk_installation)

    assert result is False


def test_is_shell_integration_enabled_returns_true_when_config_enabled() -> None:
    """Returns True when shell_integration is True in config."""
    config = GlobalConfig.test(Path("/fake/erk"), shell_integration=True)
    erk_installation = FakeErkInstallation(config=config)

    result = _is_shell_integration_enabled(erk_installation)

    assert result is True


def test_handler_passthroughs_when_shell_integration_disabled() -> None:
    """Handler returns passthrough when shell_integration is disabled (default)."""
    config = GlobalConfig.test(Path("/fake/erk"), shell_integration=False)
    deps = _create_deps(config=config, is_uvx=False)

    # Use 'wt checkout' which IS in SHELL_INTEGRATION_COMMANDS
    result = _invoke_hidden_command("wt checkout", ("feature-branch",), deps=deps)

    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_handler_passthroughs_when_config_not_exists() -> None:
    """Handler returns passthrough when config doesn't exist."""
    deps = _create_deps(config=None, is_uvx=False)

    result = _invoke_hidden_command("wt checkout", ("feature-branch",), deps=deps)

    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_handler_passthroughs_when_shell_integration_disabled_for_up() -> None:
    """Handler returns passthrough for up command when disabled."""
    config = GlobalConfig.test(Path("/fake/erk"), shell_integration=False)
    deps = _create_deps(config=config, is_uvx=False)

    result = _invoke_hidden_command("up", (), deps=deps)

    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_handler_proceeds_when_shell_integration_enabled() -> None:
    """Handler proceeds with shell integration when enabled."""
    config = GlobalConfig.test(Path("/fake/erk"), shell_integration=True)
    deps = _create_deps(config=config, is_uvx=False)

    with patch("erk.cli.shell_integration.handler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "/tmp/script.sh"

        result = _invoke_hidden_command("up", (), deps=deps)

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
    # (returns early before deps are checked)
    result = _invoke_hidden_command("checkout", ("feature-branch",))
    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)


def test_deprecated_co_alias_passthroughs() -> None:
    """Deprecated top-level 'co' alias passthroughs to CLI."""
    result = _invoke_hidden_command("co", ("feature-branch",))
    assert result == ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

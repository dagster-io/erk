"""Tests for shell integration health check."""

from pathlib import Path

from erk.core.health_checks import check_shell_integration
from erk.core.init_utils import ERK_SHELL_INTEGRATION_MARKER
from erk_shared.gateway.shell.fake import FakeShell


def test_check_shell_integration_shell_not_detected() -> None:
    """Test check when shell cannot be detected."""
    shell = FakeShell(detected_shell=None)

    result = check_shell_integration(shell)

    assert result.passed is True
    assert result.name == "shell-integration"
    assert result.info is True
    assert "Shell not detected" in result.message


def test_check_shell_integration_rc_file_not_found(tmp_path: Path) -> None:
    """Test check when RC file doesn't exist."""
    nonexistent_rc = tmp_path / ".zshrc"
    shell = FakeShell(detected_shell=("zsh", nonexistent_rc))

    result = check_shell_integration(shell)

    assert result.passed is True
    assert result.name == "shell-integration"
    assert result.info is True
    assert "Shell RC file not found" in result.message


def test_check_shell_integration_not_configured(tmp_path: Path) -> None:
    """Test check when RC file exists but integration not configured.

    Shell integration is optional - erk uses subshells by default.
    This should be info-only with no remediation action.
    """
    rc_path = tmp_path / ".zshrc"
    rc_path.write_text("# Some other content\nexport PATH=$PATH:/usr/local/bin\n")
    shell = FakeShell(detected_shell=("zsh", rc_path))

    result = check_shell_integration(shell)

    assert result.passed is True
    assert result.name == "shell-integration"
    assert result.info is True
    assert "Shell integration not configured" in result.message
    assert "zsh" in result.message
    # No remediation - shell integration is optional
    assert result.remediation is None
    # Details explain the default behavior
    assert result.details == "Optional enhancement - erk uses subshells by default"


def test_check_shell_integration_configured(tmp_path: Path) -> None:
    """Test check when shell integration is properly configured."""
    rc_path = tmp_path / ".zshrc"
    rc_path.write_text(f"{ERK_SHELL_INTEGRATION_MARKER}\nerk() {{\n  # wrapper\n}}\n")
    shell = FakeShell(detected_shell=("zsh", rc_path))

    result = check_shell_integration(shell)

    assert result.passed is True
    assert result.name == "shell-integration"
    assert result.info is False  # Not info level - it's a success
    assert "Shell integration configured" in result.message
    assert "zsh" in result.message
    assert result.remediation is None
    # Details explain what mode is being used
    assert result.details == "Using 'cd' mode instead of subshells"


def test_check_shell_integration_bash(tmp_path: Path) -> None:
    """Test check with bash shell."""
    rc_path = tmp_path / ".bashrc"
    rc_path.write_text(f"{ERK_SHELL_INTEGRATION_MARKER}\nerk() {{\n  # wrapper\n}}\n")
    shell = FakeShell(detected_shell=("bash", rc_path))

    result = check_shell_integration(shell)

    assert result.passed is True
    assert "bash" in result.message

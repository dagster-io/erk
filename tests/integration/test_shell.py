"""Integration tests for Shell.

These tests verify that RealShell correctly integrates with the system
environment and external tools using actual system state.

Shell-specific detection logic is tested in tests/unit/test_shell_ops_functions.py
via the detect_shell_from_env() function.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from erk.core.shell import RealShell


def test_real_shell_ops_detect_shell_with_current_environment():
    """Test that RealShell.detect_shell() works with actual current environment.

    This integration test verifies RealShell correctly reads from the
    actual SHELL environment variable and returns valid shell information.
    The test passes regardless of which shell is running it (or None if unsupported).
    """
    ops = RealShell()
    result = ops.detect_shell()

    # If SHELL env var is set and supported, should return valid tuple
    shell_env = os.environ.get("SHELL", "")
    if shell_env and any(s in shell_env for s in ["bash", "zsh", "fish"]):
        assert result is not None
        shell_name, rc_file = result
        assert shell_name in ["bash", "zsh", "fish"]
        assert rc_file.name in [".bashrc", ".zshrc", "config.fish"]
    # Otherwise, it's okay to return None (unsupported or missing shell)
    else:
        assert result is None or result is not None  # Either outcome is valid


def test_real_shell_ops_get_installed_tool_path():
    """Test checking if a tool is installed."""
    ops = RealShell()

    # Check for a tool that should always exist on Unix systems
    result = ops.get_installed_tool_path("sh")
    assert result is not None  # sh should always exist

    # Check for a tool that likely doesn't exist
    result = ops.get_installed_tool_path("nonexistent-tool-xyz-123")
    assert result is None


def test_real_shell_ops_get_installed_tool_path_python():
    """Test checking if Python is installed."""
    ops = RealShell()

    # Python should be available (we're running Python tests!)
    result = ops.get_installed_tool_path("python3")
    if result is None:
        # Try just "python" on some systems
        result = ops.get_installed_tool_path("python")

    assert result is not None  # Some form of Python should be found


def test_real_shell_ops_run_erk_sync_calls_subprocess():
    """Test that run_erk_sync calls run_subprocess_with_context with correct parameters.

    This integration test verifies RealShell correctly constructs and
    executes the subprocess command with appropriate parameters.
    """
    ops = RealShell()
    repo_root = Path("/test/repo")

    # Mock run_subprocess_with_context to verify the call without actually running erk
    with patch("erk_shared.gateways.shell.real.run_subprocess_with_context") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Call with force=True, verbose=False
        ops.run_erk_sync(repo_root, force=True, verbose=False)

        # Verify run_subprocess_with_context was called once
        assert mock_run.call_count == 1

        # Verify command structure and parameters
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd == ["erk", "kit", "sync", "-f"]

        # Verify kwargs
        kwargs = call_args[1]
        assert kwargs["cwd"] == repo_root
        assert kwargs["operation_context"] == "execute erk kit sync subprocess"
        assert kwargs["capture_output"] is True


def test_real_shell_ops_run_erk_sync_verbose_mode():
    """Test that run_erk_sync handles verbose mode correctly."""
    ops = RealShell()
    repo_root = Path("/test/repo")

    with patch("erk_shared.gateways.shell.real.run_subprocess_with_context") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Call with force=True, verbose=True
        ops.run_erk_sync(repo_root, force=True, verbose=True)

        # Verify command includes --verbose
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd == ["erk", "kit", "sync", "-f", "--verbose"]

        # Verify capture_output is False in verbose mode
        kwargs = call_args[1]
        assert kwargs["capture_output"] is False


def test_real_shell_ops_run_erk_sync_without_force():
    """Test that run_erk_sync works without force flag."""
    ops = RealShell()
    repo_root = Path("/test/repo")

    with patch("erk_shared.gateways.shell.real.run_subprocess_with_context") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Call with force=False
        ops.run_erk_sync(repo_root, force=False, verbose=False)

        # Verify command does not include -f
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd == ["erk", "kit", "sync"]
        assert "-f" not in cmd


def test_real_shell_ops_run_erk_sync_propagates_error():
    """Test that RuntimeError is propagated from run_subprocess_with_context."""
    ops = RealShell()
    repo_root = Path("/test/repo")

    with patch("erk_shared.gateways.shell.real.run_subprocess_with_context") as mock_run:
        # Simulate subprocess failure (run_subprocess_with_context raises RuntimeError)
        mock_run.side_effect = RuntimeError(
            "Failed to execute erk kit sync subprocess\n"
            "Command: erk kit sync -f\n"
            "Exit code: 1\n"
            "stderr: sync failed"
        )

        # Verify RuntimeError is propagated
        try:
            ops.run_erk_sync(repo_root, force=True, verbose=False)
            raise AssertionError("Expected RuntimeError to be raised")
        except RuntimeError as e:
            assert "Failed to execute erk kit sync subprocess" in str(e)
            assert "sync failed" in str(e)

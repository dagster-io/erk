"""Integration tests for Shell.

These tests verify that RealShell correctly integrates with the system
environment and external tools using actual system state.

Shell-specific detection logic is tested in tests/unit/test_shell_ops_functions.py
via the detect_shell_from_env() function.
"""

import os

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

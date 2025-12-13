"""Tests for FakeShell test infrastructure.

These tests verify that FakeShell correctly simulates shell operations,
providing reliable test doubles for CLI tests.
"""

from pathlib import Path

from tests.fakes.shell import FakeShell


def test_fake_shell_ops_initialization() -> None:
    """Test that FakeShell initializes with empty state."""
    ops = FakeShell()

    shell = ops.detect_shell()
    assert shell is None

    tool = ops.get_installed_tool_path("any-tool")
    assert tool is None


def test_fake_shell_ops_detect_shell() -> None:
    """Test that detect_shell returns pre-configured shell type."""
    shell_config = ("bash", Path.home() / ".bashrc")
    ops = FakeShell(detected_shell=shell_config)

    result = ops.detect_shell()

    assert result == ("bash", Path.home() / ".bashrc")


def test_fake_shell_ops_detect_shell_no_config() -> None:
    """Test detect_shell returns None when no shell configured."""
    ops = FakeShell(detected_shell=None)

    result = ops.detect_shell()

    assert result is None


def test_fake_shell_ops_get_installed_tool_path() -> None:
    """Test get_installed_tool_path returns configured tool path."""
    ops = FakeShell(installed_tools={"gt": "/usr/local/bin/gt"})

    result = ops.get_installed_tool_path("gt")

    assert result == "/usr/local/bin/gt"


def test_fake_shell_ops_get_installed_tool_path_missing() -> None:
    """Test get_installed_tool_path returns None for missing tool."""
    ops = FakeShell(installed_tools={"gt": "/usr/local/bin/gt"})

    result = ops.get_installed_tool_path("nonexistent")

    assert result is None


def test_fake_shell_ops_multiple_tools() -> None:
    """Test configuration with multiple tools."""
    tools = {
        "gt": "/usr/local/bin/gt",
        "gh": "/usr/local/bin/gh",
        "uv": "/opt/homebrew/bin/uv",
    }
    ops = FakeShell(installed_tools=tools)

    assert ops.get_installed_tool_path("gt") == "/usr/local/bin/gt"
    assert ops.get_installed_tool_path("gh") == "/usr/local/bin/gh"
    assert ops.get_installed_tool_path("uv") == "/opt/homebrew/bin/uv"


def test_fake_shell_ops_empty_config() -> None:
    """Test behavior with explicitly empty configuration."""
    ops = FakeShell(detected_shell=None, installed_tools={})

    assert ops.detect_shell() is None
    assert ops.get_installed_tool_path("any-tool") is None


def test_fake_shell_ops_tool_path_with_spaces() -> None:
    """Test tool path handling with spaces in path."""
    ops = FakeShell(installed_tools={"tool": "/path with spaces/bin/tool"})

    result = ops.get_installed_tool_path("tool")

    assert result == "/path with spaces/bin/tool"


def test_fake_shell_ops_different_shells() -> None:
    """Test configuration with different shell types."""
    # Bash
    ops_bash = FakeShell(detected_shell=("bash", Path.home() / ".bashrc"))
    assert ops_bash.detect_shell() == ("bash", Path.home() / ".bashrc")

    # Zsh
    ops_zsh = FakeShell(detected_shell=("zsh", Path.home() / ".zshrc"))
    assert ops_zsh.detect_shell() == ("zsh", Path.home() / ".zshrc")

    # Fish
    ops_fish = FakeShell(detected_shell=("fish", Path.home() / ".config/fish/config.fish"))
    assert ops_fish.detect_shell() == ("fish", Path.home() / ".config/fish/config.fish")

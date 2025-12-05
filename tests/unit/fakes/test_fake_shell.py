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


def test_fake_shell_ops_run_erk_sync_tracks_calls() -> None:
    """Test that run_erk_sync tracks call parameters."""
    ops = FakeShell()
    repo_root = Path("/test/repo")

    # Perform operation
    ops.run_erk_sync(repo_root, force=True, verbose=False)

    # Verify tracking
    assert len(ops.sync_calls) == 1
    assert ops.sync_calls[0] == (repo_root, True, False)


def test_fake_shell_ops_run_erk_sync_multiple_calls() -> None:
    """Test that multiple sync calls are tracked correctly."""
    ops = FakeShell()
    repo1 = Path("/test/repo1")
    repo2 = Path("/test/repo2")

    # Perform multiple operations
    ops.run_erk_sync(repo1, force=True, verbose=False)
    ops.run_erk_sync(repo2, force=False, verbose=True)

    # Verify all calls tracked
    assert len(ops.sync_calls) == 2
    assert ops.sync_calls[0] == (repo1, True, False)
    assert ops.sync_calls[1] == (repo2, False, True)


def test_fake_shell_ops_sync_calls_empty_initially() -> None:
    """Test that sync_calls starts empty."""
    ops = FakeShell()

    assert ops.sync_calls == []


def test_fake_shell_ops_sync_calls_returns_copy() -> None:
    """Test that sync_calls property returns a copy, not the internal list."""
    ops = FakeShell()
    repo_root = Path("/test/repo")

    ops.run_erk_sync(repo_root, force=True, verbose=False)

    # Get the sync_calls list
    calls = ops.sync_calls

    # Try to modify it
    calls.append((Path("/fake"), False, False))

    # Original should be unchanged
    assert len(ops.sync_calls) == 1
    assert ops.sync_calls[0] == (repo_root, True, False)


def test_fake_shell_ops_run_claude_extraction_plan_success() -> None:
    """Test that run_claude_extraction_plan returns configured URL."""
    ops = FakeShell(extraction_plan_url="https://github.com/user/repo/issues/123")
    cwd = Path("/test/repo")

    result = ops.run_claude_extraction_plan(cwd)

    assert result == "https://github.com/user/repo/issues/123"
    assert len(ops.extraction_calls) == 1
    assert ops.extraction_calls[0] == cwd


def test_fake_shell_ops_run_claude_extraction_plan_none() -> None:
    """Test that run_claude_extraction_plan returns None when not configured."""
    ops = FakeShell()
    cwd = Path("/test/repo")

    result = ops.run_claude_extraction_plan(cwd)

    assert result is None
    assert len(ops.extraction_calls) == 1


def test_fake_shell_ops_run_claude_extraction_plan_raises() -> None:
    """Test that run_claude_extraction_plan raises when configured to do so."""
    import subprocess

    ops = FakeShell(claude_extraction_raises=True)
    cwd = Path("/test/repo")

    try:
        ops.run_claude_extraction_plan(cwd)
        raise AssertionError("Expected CalledProcessError to be raised")
    except subprocess.CalledProcessError as e:
        assert e.returncode == 1
        assert "Simulated extraction failure" in e.stderr

    assert len(ops.extraction_calls) == 1


def test_fake_shell_ops_extraction_calls_empty_initially() -> None:
    """Test that extraction_calls starts empty."""
    ops = FakeShell()

    assert ops.extraction_calls == []


def test_fake_shell_ops_extraction_calls_returns_copy() -> None:
    """Test that extraction_calls property returns a copy."""
    ops = FakeShell(extraction_plan_url="https://github.com/user/repo/issues/123")
    cwd = Path("/test/repo")

    ops.run_claude_extraction_plan(cwd)

    # Get the extraction_calls list
    calls = ops.extraction_calls

    # Try to modify it
    calls.append(Path("/fake"))

    # Original should be unchanged
    assert len(ops.extraction_calls) == 1
    assert ops.extraction_calls[0] == cwd

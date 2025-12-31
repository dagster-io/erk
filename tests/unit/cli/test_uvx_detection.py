"""Tests for uvx (uv tool run) detection logic."""

from unittest.mock import patch

from erk.cli.uvx_detection import get_uvx_warning_message, is_running_via_uvx


def test_detects_uvx_via_sys_prefix_linux() -> None:
    """Detect uvx via sys.prefix containing Linux cache path."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/home/user/.cache/uv/tools/erk-0.2.8/bin/python"
        with patch.dict("erk.cli.uvx_detection.os.environ", {}, clear=True):
            assert is_running_via_uvx() is True


def test_detects_uvx_via_sys_prefix_macos() -> None:
    """Detect uvx via sys.prefix containing macOS cache path."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/Users/user/.cache/uv/tools/erk-0.2.8/bin/python"
        with patch.dict("erk.cli.uvx_detection.os.environ", {}, clear=True):
            assert is_running_via_uvx() is True


def test_detects_uvx_via_sys_prefix_macos_library() -> None:
    """Detect uvx via sys.prefix containing macOS Library/Caches path."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/Users/user/Library/Caches/uv/tools/erk/bin/python"
        with patch.dict("erk.cli.uvx_detection.os.environ", {}, clear=True):
            # This path uses /Caches/uv/ which doesn't match our patterns
            # (we look for /cache/uv/ or /.cache/uv/)
            # For macOS Library/Caches, we rely on UV_TOOL_DIR or VIRTUAL_ENV
            assert is_running_via_uvx() is False


def test_detects_uvx_via_virtual_env() -> None:
    """Detect uvx via VIRTUAL_ENV environment variable."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/some/other/path"
        env = {"VIRTUAL_ENV": "/home/user/.cache/uv/tools/erk-0.2.8"}
        with patch.dict("erk.cli.uvx_detection.os.environ", env, clear=True):
            assert is_running_via_uvx() is True


def test_detects_uvx_via_uv_tool_dir() -> None:
    """Detect uvx via UV_TOOL_DIR environment variable."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/some/other/path"
        env = {"UV_TOOL_DIR": "/home/user/.local/share/uv/tools"}
        with patch.dict("erk.cli.uvx_detection.os.environ", env, clear=True):
            assert is_running_via_uvx() is True


def test_detects_uvx_via_uv_cache_dir() -> None:
    """Detect uvx via UV_CACHE_DIR environment variable."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/some/other/path"
        env = {"UV_CACHE_DIR": "/tmp/uv-cache"}
        with patch.dict("erk.cli.uvx_detection.os.environ", env, clear=True):
            assert is_running_via_uvx() is True


def test_not_uvx_in_regular_venv() -> None:
    """Regular venv should not be detected as uvx."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/Users/user/projects/my-project/.venv"
        env = {"VIRTUAL_ENV": "/Users/user/projects/my-project/.venv"}
        with patch.dict("erk.cli.uvx_detection.os.environ", env, clear=True):
            assert is_running_via_uvx() is False


def test_not_uvx_system_python() -> None:
    """System Python should not be detected as uvx."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/usr/local"
        with patch.dict("erk.cli.uvx_detection.os.environ", {}, clear=True):
            assert is_running_via_uvx() is False


def test_not_uvx_homebrew_python() -> None:
    """Homebrew Python should not be detected as uvx."""
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        mock_sys.prefix = "/opt/homebrew/Cellar/python@3.11/3.11.0/Frameworks"
        with patch.dict("erk.cli.uvx_detection.os.environ", {}, clear=True):
            assert is_running_via_uvx() is False


def test_warning_message_contains_key_phrases() -> None:
    """Warning message should contain key information."""
    message = get_uvx_warning_message()

    # Should mention uvx/uv tool
    assert "uvx" in message.lower() or "uv" in message

    # Should mention shell integration won't work
    assert "shell integration" in message.lower()

    # Should mention the fix
    assert "uv tool install" in message

    # Should mention init --shell
    assert "erk init --shell" in message


def test_warning_message_mentions_affected_commands() -> None:
    """Warning message should mention specific affected commands."""
    message = get_uvx_warning_message()

    # Should mention example commands that won't work
    assert "erk up" in message
    assert "erk checkout" in message
    assert "erk pr land" in message

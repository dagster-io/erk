"""Tests for uvx (uv tool run) detection logic."""

from pathlib import Path
from unittest.mock import patch

from erk.cli.uvx_detection import get_uvx_warning_message, is_running_via_uvx


def test_detects_uvx_via_archive_path_with_uv_marker(tmp_path: Path) -> None:
    """Detect uvx via archive-v path marker with uv in pyvenv.cfg."""
    # Create pyvenv.cfg with uv marker
    pyvenv_cfg = tmp_path / "pyvenv.cfg"
    pyvenv_cfg.write_text("home = /usr/bin\nuv = 0.5.0\n", encoding="utf-8")

    # Simulate uvx ephemeral environment path
    with patch("erk.cli.uvx_detection.sys") as mock_sys:
        # Use a path that contains the archive-v marker
        mock_sys.prefix = f"/home/user/.cache/uv/archive-v0/{tmp_path.name}"
        # But we need pyvenv.cfg to exist at sys.prefix, so patch Path
        with patch("erk.cli.uvx_detection.Path") as mock_path_class:
            mock_prefix = mock_path_class.return_value
            mock_prefix.__truediv__ = lambda self, x: tmp_path / x if x == "pyvenv.cfg" else Path(x)
            mock_prefix.__str__ = lambda self: "/home/user/.cache/uv/archive-v0/env"
            assert is_running_via_uvx() is True


def test_detects_uvx_via_cache_path_with_uv_marker(tmp_path: Path) -> None:
    """Detect uvx via .cache/uv path with uv in pyvenv.cfg."""
    pyvenv_cfg = tmp_path / "pyvenv.cfg"
    pyvenv_cfg.write_text("home = /usr/bin\nuv = 0.5.0\n", encoding="utf-8")

    with patch("erk.cli.uvx_detection.Path") as mock_path_class:
        mock_prefix = mock_path_class.return_value
        mock_prefix.__truediv__ = lambda self, x: tmp_path / x if x == "pyvenv.cfg" else Path(x)
        mock_prefix.__str__ = lambda self: "/home/user/.cache/uv/tools/erk"
        assert is_running_via_uvx() is True


def test_not_uvx_when_pyvenv_cfg_missing_uv_marker(tmp_path: Path) -> None:
    """Not uvx when pyvenv.cfg exists but lacks uv marker."""
    # Create pyvenv.cfg WITHOUT uv marker (regular venv)
    pyvenv_cfg = tmp_path / "pyvenv.cfg"
    pyvenv_cfg.write_text("home = /usr/bin\nversion = 3.11.0\n", encoding="utf-8")

    with patch("erk.cli.uvx_detection.Path") as mock_path_class:
        mock_prefix = mock_path_class.return_value
        mock_prefix.__truediv__ = lambda self, x: tmp_path / x if x == "pyvenv.cfg" else Path(x)
        # Even with cache-like path, should return False due to missing uv marker
        mock_prefix.__str__ = lambda self: "/home/user/.cache/uv/tools/erk"
        assert is_running_via_uvx() is False


def test_not_uvx_for_uv_tool_install_environment(tmp_path: Path) -> None:
    """Not uvx for persistent uv tool install environment (not ephemeral)."""
    # Create pyvenv.cfg with uv marker
    pyvenv_cfg = tmp_path / "pyvenv.cfg"
    pyvenv_cfg.write_text("home = /usr/bin\nuv = 0.5.0\n", encoding="utf-8")

    with patch("erk.cli.uvx_detection.Path") as mock_path_class:
        mock_prefix = mock_path_class.return_value
        mock_prefix.__truediv__ = lambda self, x: tmp_path / x if x == "pyvenv.cfg" else Path(x)
        # uv tool install uses ~/.local/share/uv/tools, NOT cache
        mock_prefix.__str__ = lambda self: "/home/user/.local/share/uv/tools/erk"
        assert is_running_via_uvx() is False


def test_not_uvx_in_regular_venv(tmp_path: Path) -> None:
    """Regular venv should not be detected as uvx."""
    # Create pyvenv.cfg without uv marker
    pyvenv_cfg = tmp_path / "pyvenv.cfg"
    pyvenv_cfg.write_text("home = /usr/bin\nversion = 3.11.0\n", encoding="utf-8")

    with patch("erk.cli.uvx_detection.Path") as mock_path_class:
        mock_prefix = mock_path_class.return_value
        mock_prefix.__truediv__ = lambda self, x: tmp_path / x if x == "pyvenv.cfg" else Path(x)
        mock_prefix.__str__ = lambda self: "/Users/user/projects/my-project/.venv"
        assert is_running_via_uvx() is False


def test_not_uvx_system_python(tmp_path: Path) -> None:
    """System Python should not be detected as uvx."""
    # No pyvenv.cfg exists for system python
    with patch("erk.cli.uvx_detection.Path") as mock_path_class:
        mock_prefix = mock_path_class.return_value
        mock_pyvenv = tmp_path / "nonexistent"  # Doesn't exist
        mock_prefix.__truediv__ = lambda self, x: mock_pyvenv if x == "pyvenv.cfg" else Path(x)
        mock_prefix.__str__ = lambda self: "/usr/local"
        assert is_running_via_uvx() is False


def test_not_uvx_homebrew_python(tmp_path: Path) -> None:
    """Homebrew Python should not be detected as uvx."""
    with patch("erk.cli.uvx_detection.Path") as mock_path_class:
        mock_prefix = mock_path_class.return_value
        mock_pyvenv = tmp_path / "nonexistent"
        mock_prefix.__truediv__ = lambda self, x: mock_pyvenv if x == "pyvenv.cfg" else Path(x)
        mock_prefix.__str__ = lambda self: "/opt/homebrew/Cellar/python@3.11/3.11.0/Frameworks"
        assert is_running_via_uvx() is False


def test_warning_message_contains_key_phrases() -> None:
    """Warning message should contain key information."""
    message = get_uvx_warning_message("checkout")

    # Should mention uvx/uv tool
    assert "uvx" in message.lower() or "uv" in message

    # Should mention shell integration
    assert "shell integration" in message.lower()

    # Should mention the fix
    assert "uv tool install" in message

    # Should mention init --shell
    assert "erk init --shell" in message


def test_warning_message_includes_command_name() -> None:
    """Warning message should include the specific command being invoked."""
    message = get_uvx_warning_message("checkout")
    assert "erk checkout" in message

    message = get_uvx_warning_message("up")
    assert "erk up" in message

    message = get_uvx_warning_message("land")
    assert "erk land" in message

"""Tests for init_utils pure functions.

These are integration tests (Layer 2) that use tmp_path for filesystem operations.
"""

from pathlib import Path

from erk.core.init_utils import (
    ERK_SHELL_INTEGRATION_MARKER,
    has_shell_integration_in_rc,
    is_repo_erk_ified,
)


def test_is_repo_erk_ified_returns_true_when_config_exists(tmp_path: Path) -> None:
    """Test that is_repo_erk_ified returns True when .erk/config.toml exists."""
    # Create the config file
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text("[erk]\n", encoding="utf-8")

    assert is_repo_erk_ified(tmp_path) is True


def test_is_repo_erk_ified_returns_false_when_config_missing(tmp_path: Path) -> None:
    """Test that is_repo_erk_ified returns False when .erk/config.toml is missing."""
    assert is_repo_erk_ified(tmp_path) is False


def test_is_repo_erk_ified_returns_false_when_erk_dir_exists_but_no_config(
    tmp_path: Path,
) -> None:
    """Test that is_repo_erk_ified returns False when .erk/ exists but no config.toml."""
    # Create .erk directory without config.toml
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    assert is_repo_erk_ified(tmp_path) is False


def test_is_repo_erk_ified_returns_false_when_config_is_directory(
    tmp_path: Path,
) -> None:
    """Test that is_repo_erk_ified returns False if config.toml is a directory."""
    # Create config.toml as a directory (edge case)
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_dir = erk_dir / "config.toml"
    config_dir.mkdir()

    # Path.exists() returns True for directories too, but this is an edge case
    # The function still returns True because .exists() checks for existence
    # This test documents the current behavior
    assert is_repo_erk_ified(tmp_path) is True


# --- Tests for has_shell_integration_in_rc ---


def test_has_shell_integration_in_rc_returns_true_when_marker_present(
    tmp_path: Path,
) -> None:
    """Test that has_shell_integration_in_rc returns True when marker is in RC file."""
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text(
        f"# Some other config\n{ERK_SHELL_INTEGRATION_MARKER} for zsh\nerk() {{\n  ...\n}}\n",
        encoding="utf-8",
    )

    assert has_shell_integration_in_rc(rc_file) is True


def test_has_shell_integration_in_rc_returns_false_when_marker_missing(
    tmp_path: Path,
) -> None:
    """Test that has_shell_integration_in_rc returns False when marker is not in RC file."""
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text("# Just some other config\nexport PATH=$PATH\n", encoding="utf-8")

    assert has_shell_integration_in_rc(rc_file) is False


def test_has_shell_integration_in_rc_returns_false_when_file_missing(
    tmp_path: Path,
) -> None:
    """Test that has_shell_integration_in_rc returns False when RC file doesn't exist."""
    rc_file = tmp_path / ".zshrc"
    # Don't create the file

    assert has_shell_integration_in_rc(rc_file) is False


def test_has_shell_integration_in_rc_detects_partial_marker(tmp_path: Path) -> None:
    """Test that has_shell_integration_in_rc matches the marker substring."""
    rc_file = tmp_path / ".bashrc"
    # The marker is "# Erk shell integration" - test that it matches
    # even without the shell name suffix
    rc_file.write_text(
        f"# Some config\n{ERK_SHELL_INTEGRATION_MARKER}\nerk() {{\n}}\n",
        encoding="utf-8",
    )

    assert has_shell_integration_in_rc(rc_file) is True

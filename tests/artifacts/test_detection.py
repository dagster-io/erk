"""Tests for artifact detection utilities."""

from pathlib import Path

from erk.artifacts.detection import is_in_erk_repo


def test_is_in_erk_repo_true(tmp_path: Path) -> None:
    """Returns True when pyproject.toml contains name = "erk"."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    assert is_in_erk_repo(tmp_path) is True


def test_is_in_erk_repo_false_different_name(tmp_path: Path) -> None:
    """Returns False when pyproject.toml has different project name."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "other-project"\n', encoding="utf-8")

    assert is_in_erk_repo(tmp_path) is False


def test_is_in_erk_repo_false_no_pyproject(tmp_path: Path) -> None:
    """Returns False when no pyproject.toml exists."""
    assert is_in_erk_repo(tmp_path) is False

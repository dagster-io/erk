"""Tests for review configuration reading."""

from pathlib import Path

from erk.review.config import read_review_exclude_patterns


def test_reads_exclude_patterns(tmp_path: Path) -> None:
    """Read exclude patterns from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.erk.reviews]\nexclude = [".claude/skills/", "vendor/"]\n',
        encoding="utf-8",
    )

    result = read_review_exclude_patterns(tmp_path)

    assert result == (".claude/skills/", "vendor/")


def test_returns_empty_when_no_pyproject(tmp_path: Path) -> None:
    """Return empty tuple when pyproject.toml doesn't exist."""
    result = read_review_exclude_patterns(tmp_path)

    assert result == ()


def test_returns_empty_when_no_erk_section(tmp_path: Path) -> None:
    """Return empty tuple when [tool.erk.reviews] section is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.ruff]\nexclude = [".claude/skills/"]\n',
        encoding="utf-8",
    )

    result = read_review_exclude_patterns(tmp_path)

    assert result == ()


def test_returns_empty_when_no_exclude_key(tmp_path: Path) -> None:
    """Return empty tuple when exclude key is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.erk.reviews]\n",
        encoding="utf-8",
    )

    result = read_review_exclude_patterns(tmp_path)

    assert result == ()


def test_returns_empty_when_exclude_not_list(tmp_path: Path) -> None:
    """Return empty tuple when exclude is not a list."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.erk.reviews]\nexclude = ".claude/skills/"\n',
        encoding="utf-8",
    )

    result = read_review_exclude_patterns(tmp_path)

    assert result == ()


def test_filters_non_string_items(tmp_path: Path) -> None:
    """Filter out non-string items from exclude list."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.erk.reviews]\nexclude = [".claude/skills/", 42]\n',
        encoding="utf-8",
    )

    result = read_review_exclude_patterns(tmp_path)

    assert result == (".claude/skills/",)

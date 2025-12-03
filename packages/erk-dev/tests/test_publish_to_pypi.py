"""Tests for publish_to_pypi git status parsing.

These tests verify the git status filtering logic correctly handles:
- Filenames with spaces
- Various git status codes
- Exclusion of specific files
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_user_output():
    """Mock user_output globally to avoid circular import issues."""
    with patch("erk_dev.cli.output.user_output"):
        yield


def get_shared():
    """Lazy import to avoid circular dependency during test collection."""
    from erk_dev.commands.publish_to_pypi import shared

    return shared


def test_filter_git_status_handles_spaces_in_filenames() -> None:
    """Test that filenames with spaces are parsed correctly.

    This is the critical bug fix - the old code used split() which broke
    on filenames with spaces. Example:
        " M my file.txt" split to ['M', 'my', 'file.txt']
        parts[-1] was 'file.txt', not 'my file.txt'
    """
    status = " M my file.txt\n M another file.py"
    excluded = set()

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 2
    assert " M my file.txt" in result
    assert " M another file.py" in result


def test_filter_git_status_excludes_specified_files() -> None:
    """Test that specified files are properly excluded."""
    status = " M pyproject.toml\n M uv.lock\n M other_file.py"
    excluded = {"pyproject.toml", "uv.lock"}

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 1
    assert " M other_file.py" in result
    assert " M pyproject.toml" not in result
    assert " M uv.lock" not in result


def test_filter_git_status_excludes_files_with_spaces() -> None:
    """Test that excluded files with spaces work correctly."""
    status = " M my file.txt\n M other.py"
    excluded = {"my file.txt"}

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 1
    assert " M other.py" in result
    assert " M my file.txt" not in result


def test_filter_git_status_handles_various_status_codes() -> None:
    """Test parsing of different git status codes.

    Git porcelain format uses 2-character status codes:
    - ' M' = modified in working tree
    - 'M ' = modified in index
    - 'MM' = modified in both
    - 'A ' = added to index
    - 'D ' = deleted from index
    - '??' = untracked
    - 'R ' = renamed
    """
    status = (
        " M modified_worktree.py\n"
        "M  modified_index.py\n"
        "MM modified_both.py\n"
        "A  added.py\n"
        "D  deleted.py\n"
        "?? untracked.py\n"
        "R  renamed.py"
    )
    excluded = set()

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 7
    assert " M modified_worktree.py" in result
    assert "M  modified_index.py" in result
    assert "MM modified_both.py" in result
    assert "A  added.py" in result
    assert "D  deleted.py" in result
    assert "?? untracked.py" in result
    assert "R  renamed.py" in result


def test_filter_git_status_handles_empty_status() -> None:
    """Test that empty status returns empty list."""
    status = ""
    excluded = {"pyproject.toml"}

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 0


def test_filter_git_status_handles_only_excluded_files() -> None:
    """Test when all files are excluded."""
    status = " M pyproject.toml\n M uv.lock"
    excluded = {"pyproject.toml", "uv.lock"}

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 0


def test_filter_git_status_minimum_line_length() -> None:
    """Test that lines shorter than minimum are ignored."""
    status = "M\nMM\nMMM\n M file.py"
    excluded = set()

    result = get_shared().filter_git_status(status, excluded)

    # Only "MMM" (len=3) and " M file.py" should be ignored/included
    # "M" (len=1) and "MM" (len=2) are too short
    # "MMM" (len=3) is still too short (need at least 4: "XY f")
    # Only " M file.py" should pass
    assert len(result) == 1
    assert " M file.py" in result


def test_filter_git_status_complex_scenario() -> None:
    """Test a complex real-world scenario.

    Simulate a repo with:
    - Modified pyproject.toml and uv.lock (should be excluded)
    - Modified files with spaces in names (should be included)
    - Various other changes (should be included)
    """
    status = (
        " M pyproject.toml\n"
        " M uv.lock\n"
        " M my config file.toml\n"
        "?? new file with spaces.py\n"
        "M  src/module.py\n"
        "MM tests/test file.py"
    )
    excluded = {"pyproject.toml", "uv.lock"}

    result = get_shared().filter_git_status(status, excluded)

    assert len(result) == 4
    assert " M my config file.toml" in result
    assert "?? new file with spaces.py" in result
    assert "M  src/module.py" in result
    assert "MM tests/test file.py" in result
    # Excluded files should not be in result
    assert " M pyproject.toml" not in result
    assert " M uv.lock" not in result

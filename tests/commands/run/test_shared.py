"""Unit tests for run command shared utilities.

Tests the extract_plan_number helper function for parsing display_title formats.
"""

from erk.cli.commands.run.shared import extract_plan_number


def test_extract_plan_number_new_format() -> None:
    """Test parsing new format: '123:abc456' → 123."""
    assert extract_plan_number("123:abc456") == 123
    assert extract_plan_number("1:x") == 1
    assert extract_plan_number("999:distinct-id-here") == 999


def test_extract_plan_number_old_format_returns_none() -> None:
    """Test old format: 'Issue title [abc123]' → None."""
    # Old format has title first, then distinct_id in brackets
    assert extract_plan_number("Add user authentication [abc123]") is None
    assert extract_plan_number("Fix bug in parser [xyz789]") is None


def test_extract_plan_number_with_colon_in_title_returns_none() -> None:
    """Test titles with colons but non-numeric prefix → None."""
    # These look like they have colons but the prefix isn't a number
    assert extract_plan_number("Feature: Add caching [abc]") is None
    assert extract_plan_number("Bug fix: memory leak [xyz]") is None


def test_extract_plan_number_none_or_empty() -> None:
    """Test None or empty string → None."""
    assert extract_plan_number(None) is None
    assert extract_plan_number("") is None


def test_extract_plan_number_no_colon() -> None:
    """Test string without colon → None."""
    assert extract_plan_number("no colon here") is None
    assert extract_plan_number("12345") is None


def test_extract_plan_number_whitespace() -> None:
    """Test handling of whitespace."""
    assert extract_plan_number(" 123:abc") == 123
    assert extract_plan_number("123 :abc") == 123

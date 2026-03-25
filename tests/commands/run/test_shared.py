"""Unit tests for run command shared utilities.

Tests the extract_pr_number helper function for parsing display_title formats.
"""

from erk.cli.commands.run.shared import extract_pr_number

# --- extract_pr_number tests ---


def test_extract_pr_number_pr_address_format() -> None:
    """Test pr-address format: 'pr-address:#456:abc123' → 456."""
    assert extract_pr_number("pr-address:#456:abc123") == 456


def test_extract_pr_number_plan_implement_old_format() -> None:
    """Test old plan-implement format: '8559:#460:abc123' → 460."""
    assert extract_pr_number("8559:#460:abc123") == 460
    assert extract_pr_number("142:#460:abc456") == 460


def test_extract_pr_number_plan_implement_new_format() -> None:
    """Test new plan-implement format: 'branch-name (#460):abc456' → 460."""
    assert extract_pr_number("plnd/fix-auth-bug-01-15-1430 (#460):abc456") == 460
    assert extract_pr_number("plnd/add-feature (#8559):xyz123") == 8559


def test_extract_pr_number_one_shot_format() -> None:
    """Test one-shot format: 'one-shot:#458:abc123' → 458."""
    assert extract_pr_number("one-shot:#458:abc123") == 458


def test_extract_pr_number_rebase_format() -> None:
    """Test rebase format: 'rebase:#456:abc123' → 456."""
    assert extract_pr_number("rebase:#456:abc123") == 456


def test_extract_pr_number_rewrite_format() -> None:
    """Test rewrite format: 'rewrite:#456:abc123' → 456."""
    assert extract_pr_number("rewrite:#456:abc123") == 456


def test_extract_pr_number_old_format_returns_none() -> None:
    """Test old plan-implement format without #: '8559:abc123' → None."""
    assert extract_pr_number("8559:abc123") is None
    assert extract_pr_number("142:abc456") is None


def test_extract_pr_number_legacy_format_returns_none() -> None:
    """Test legacy format: 'Some title [abc123]' → None."""
    assert extract_pr_number("Some legacy title [abc123]") is None
    assert extract_pr_number("Add user authentication [xyz789]") is None


def test_extract_pr_number_none_or_empty() -> None:
    """Test None or empty string → None."""
    assert extract_pr_number(None) is None
    assert extract_pr_number("") is None

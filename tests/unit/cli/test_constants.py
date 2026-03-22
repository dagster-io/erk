"""Unit tests for CLI constants."""

from erk.cli.constants import has_pr_title_prefix


def test_has_pr_title_prefix_erk_pr() -> None:
    """Title with [erk-pr] prefix returns True."""
    assert has_pr_title_prefix("[erk-pr] My plan title") is True


def test_has_pr_title_prefix_erk_learn() -> None:
    """Title with [erk-learn] prefix returns True."""
    assert has_pr_title_prefix("[erk-learn] My learn plan") is True


def test_has_pr_title_prefix_missing() -> None:
    """Title without recognized prefix returns False."""
    assert has_pr_title_prefix("No prefix plan") is False


def test_has_pr_title_prefix_partial() -> None:
    """Title with partial prefix (missing space) returns False."""
    assert has_pr_title_prefix("[erk-pr]No space") is False

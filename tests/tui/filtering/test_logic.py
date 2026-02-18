"""Tests for filter_plans logic."""

from erk.tui.filtering.logic import filter_plans
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_filter_by_title_substring() -> None:
    """Filters plans by title substring match."""
    plans = [
        make_plan_row(1, "Add user authentication"),
        make_plan_row(2, "Fix login bug"),
        make_plan_row(3, "Refactor database"),
    ]
    result = filter_plans(plans, "login")
    assert len(result) == 1
    assert result[0].plan_id == 2


def test_filter_by_issue_number() -> None:
    """Filters plans by issue number."""
    plans = [
        make_plan_row(123, "Plan A"),
        make_plan_row(456, "Plan B"),
        make_plan_row(789, "Plan C"),
    ]
    result = filter_plans(plans, "456")
    assert len(result) == 1
    assert result[0].plan_id == 456


def test_filter_by_pr_number() -> None:
    """Filters plans by PR number."""
    plans = [
        make_plan_row(1, "Plan A", pr_number=100),
        make_plan_row(2, "Plan B", pr_number=200),
        make_plan_row(3, "Plan C"),  # No PR
    ]
    result = filter_plans(plans, "200")
    assert len(result) == 1
    assert result[0].plan_id == 2


def test_empty_query_returns_all() -> None:
    """Empty query returns all plans unchanged."""
    plans = [
        make_plan_row(1, "Plan A"),
        make_plan_row(2, "Plan B"),
        make_plan_row(3, "Plan C"),
    ]
    result = filter_plans(plans, "")
    assert len(result) == 3
    assert result == plans


def test_case_insensitive_title_match() -> None:
    """Title matching is case-insensitive."""
    plans = [
        make_plan_row(1, "Add USER Authentication"),
        make_plan_row(2, "Fix Login Bug"),
    ]
    result = filter_plans(plans, "authentication")
    assert len(result) == 1
    assert result[0].plan_id == 1


def test_case_insensitive_query() -> None:
    """Query case doesn't matter."""
    plans = [
        make_plan_row(1, "Add user authentication"),
    ]
    result = filter_plans(plans, "USER")
    assert len(result) == 1
    assert result[0].plan_id == 1


def test_no_matches_returns_empty() -> None:
    """No matches returns empty list."""
    plans = [
        make_plan_row(1, "Plan A"),
        make_plan_row(2, "Plan B"),
    ]
    result = filter_plans(plans, "nonexistent")
    assert len(result) == 0


def test_partial_issue_number_match() -> None:
    """Partial issue number match works."""
    plans = [
        make_plan_row(123, "Plan A"),
        make_plan_row(456, "Plan B"),
        make_plan_row(1234, "Plan C"),
    ]
    # "12" matches both 123 and 1234
    result = filter_plans(plans, "12")
    assert len(result) == 2
    assert result[0].plan_id == 123
    assert result[1].plan_id == 1234


def test_filter_by_author() -> None:
    """Filters plans by author name."""
    plans = [
        make_plan_row(1, "Plan A", author="alice"),
        make_plan_row(2, "Plan B", author="bob"),
        make_plan_row(3, "Plan C", author="alice-smith"),
    ]
    result = filter_plans(plans, "alice")
    assert len(result) == 2
    assert result[0].plan_id == 1
    assert result[1].plan_id == 3


def test_multiple_matches_preserved_order() -> None:
    """Multiple matches preserve original order."""
    plans = [
        make_plan_row(1, "First feature"),
        make_plan_row(2, "Second feature"),
        make_plan_row(3, "Third feature"),
    ]
    result = filter_plans(plans, "feature")
    assert len(result) == 3
    assert result[0].plan_id == 1
    assert result[1].plan_id == 2
    assert result[2].plan_id == 3

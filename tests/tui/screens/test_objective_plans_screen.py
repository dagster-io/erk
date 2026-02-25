"""Tests for ObjectivePlansScreen formatting and behavior."""

from erk.tui.screens.objective_plans_screen import _format_plan_rows
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_format_plan_rows_empty_list() -> None:
    """Empty list returns no formatted lines."""
    result = _format_plan_rows([])
    assert result == []


def test_format_plan_rows_plan_without_pr() -> None:
    """Plan without PR shows only plan ID and title."""
    row = make_plan_row(7911, "Delete issue plan backend")
    result = _format_plan_rows([row])
    assert len(result) == 1
    assert "#7911" in result[0]
    assert "Delete issue plan backend" in result[0]
    assert "PR" not in result[0]


def test_format_plan_rows_plan_with_pr() -> None:
    """Plan with PR shows plan ID, title, PR display, and state."""
    row = make_plan_row(
        7911,
        "Delete issue plan backend",
        pr_number=8141,
        pr_state="OPEN",
    )
    result = _format_plan_rows([row])
    assert len(result) == 1
    assert "#7911" in result[0]
    assert "Delete issue plan backend" in result[0]
    assert "PR #8141" in result[0]
    assert "OPEN" in result[0]


def test_format_plan_rows_multiple_plans() -> None:
    """Multiple plans each get their own formatted line."""
    rows = [
        make_plan_row(7911, "Delete issue plan backend", pr_number=8141, pr_state="OPEN"),
        make_plan_row(7813, "Eliminate git checkouts", pr_number=7991, pr_state="MERGED"),
        make_plan_row(7724, "Rename issue to plan"),
    ]
    result = _format_plan_rows(rows)
    assert len(result) == 3
    assert "#7911" in result[0]
    assert "#7813" in result[1]
    assert "#7724" in result[2]


def test_format_plan_rows_plan_with_pr_no_state() -> None:
    """Plan with PR but no state omits state display."""
    row = make_plan_row(
        7911,
        "Some plan",
        pr_number=8141,
    )
    result = _format_plan_rows([row])
    assert len(result) == 1
    assert "PR #8141" in result[0]
    # pr_state is None, so no state suffix
    assert "OPEN" not in result[0]
    assert "MERGED" not in result[0]

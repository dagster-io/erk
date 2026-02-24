"""Tests for next_steps formatting."""

from erk_shared.output.next_steps import (
    IssueNextSteps,
    PlannedPRNextSteps,
    format_next_steps_plain,
    format_planned_pr_next_steps_plain,
)


def test_planned_pr_next_steps_constructs_with_all_params() -> None:
    """PlannedPRNextSteps constructs correctly with pr_number, branch_name, and url."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.pr_number == 42
    assert s.branch_name == "plan-feature-foo"
    assert s.url == "https://github.com/org/repo/pull/42"


def test_planned_pr_next_steps_view_returns_url() -> None:
    """view returns the URL directly."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.view == "https://github.com/org/repo/pull/42"


def test_planned_pr_next_steps_checkout_branch_and_implement_uses_branch_name() -> None:
    """checkout_branch_and_implement uses branch_name, not pr_number."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert "plan-feature-foo" in s.checkout_branch_and_implement
    assert "42" not in s.checkout_branch_and_implement


def test_planned_pr_next_steps_checkout_uses_pr_number() -> None:
    """checkout uses --for-plan with pr_number."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.checkout == "erk br co --for-plan 42"


def test_issue_next_steps_checkout_uses_co() -> None:
    """IssueNextSteps.checkout uses erk br co --for-plan."""
    s = IssueNextSteps(issue_number=99, url="https://github.com/org/repo/issues/99")
    assert s.checkout == "erk br co --for-plan 99"


def test_issue_next_steps_view_returns_url() -> None:
    """IssueNextSteps.view returns the URL directly."""
    s = IssueNextSteps(issue_number=99, url="https://github.com/org/repo/issues/99")
    assert s.view == "https://github.com/org/repo/issues/99"


def test_format_planned_pr_next_steps_plain_uses_for_plan() -> None:
    """format_planned_pr_next_steps_plain uses --for-plan command."""
    output = format_planned_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert "erk br co --for-plan 42" in output


def test_format_planned_pr_next_steps_plain_contains_url() -> None:
    """format_planned_pr_next_steps_plain shows URL in view line."""
    output = format_planned_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert "https://github.com/org/repo/pull/42" in output


def test_format_next_steps_plain_uses_co() -> None:
    """format_next_steps_plain uses erk br co --for-plan."""
    output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
    assert "erk br co --for-plan 99" in output
    assert "erk br create" not in output


def test_format_next_steps_plain_contains_implement() -> None:
    """format_next_steps_plain includes implement command."""
    output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
    assert "erk implement --dangerous" in output


def test_format_next_steps_plain_contains_url() -> None:
    """format_next_steps_plain shows URL in view line."""
    output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
    assert "https://github.com/org/repo/issues/99" in output


def test_format_planned_pr_next_steps_plain_contains_implement() -> None:
    """format_planned_pr_next_steps_plain includes implement command."""
    output = format_planned_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert "erk implement --dangerous" in output

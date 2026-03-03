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


def test_planned_pr_next_steps_checkout_uses_pr_number() -> None:
    """checkout uses --for-plan with pr_number."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.checkout == "erk br co --for-plan 42"


def test_planned_pr_next_steps_implement_new_br() -> None:
    """implement_new_br uses --for-plan with erk implement (non-dangerous)."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.implement_new_br == ('source "$(erk br co --for-plan 42 --script)" && erk implement')


def test_planned_pr_next_steps_implement_new_br_dangerous() -> None:
    """implement_new_br_dangerous uses -d flag."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.implement_new_br_dangerous == (
        'source "$(erk br co --for-plan 42 --script)" && erk implement -d'
    )


def test_planned_pr_next_steps_implement_new_wt() -> None:
    """implement_new_wt uses --new-slot with erk implement (non-dangerous)."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.implement_new_wt == (
        'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement'
    )


def test_planned_pr_next_steps_implement_new_wt_dangerous() -> None:
    """implement_new_wt_dangerous uses --new-slot with -d flag."""
    s = PlannedPRNextSteps(
        pr_number=42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert s.implement_new_wt_dangerous == (
        'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement -d'
    )


def test_issue_next_steps_checkout_uses_co() -> None:
    """IssueNextSteps.checkout uses erk br co --for-plan."""
    s = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
    assert s.checkout == "erk br co --for-plan 99"


def test_issue_next_steps_view_returns_url() -> None:
    """IssueNextSteps.view returns the URL directly."""
    s = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
    assert s.view == "https://github.com/org/repo/issues/99"


def test_issue_next_steps_implement_new_br() -> None:
    """IssueNextSteps.implement_new_br uses --for-plan with erk implement."""
    s = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
    assert s.implement_new_br == ('source "$(erk br co --for-plan 99 --script)" && erk implement')


def test_issue_next_steps_implement_new_wt() -> None:
    """IssueNextSteps.implement_new_wt uses --new-slot with erk implement."""
    s = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
    assert s.implement_new_wt == (
        'source "$(erk br co --new-slot --for-plan 99 --script)" && erk implement'
    )


def test_format_planned_pr_next_steps_plain_hierarchical_format() -> None:
    """format_planned_pr_next_steps_plain produces hierarchical output."""
    output = format_planned_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert "Implement plan #42:" in output
    assert "In new br:" in output
    assert "In new wt:" in output
    assert "(dangerously):" in output
    assert "Checkout plan #42:" in output
    assert "Dispatch to queue:" in output


def test_format_planned_pr_next_steps_plain_contains_implement() -> None:
    """format_planned_pr_next_steps_plain includes implement commands."""
    output = format_planned_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", url="https://github.com/org/repo/pull/42"
    )
    assert "erk implement" in output
    assert "erk implement -d" in output


def test_format_next_steps_plain_hierarchical_format() -> None:
    """format_next_steps_plain produces hierarchical output."""
    output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
    assert "Implement plan #99:" in output
    assert "In new br:" in output
    assert "In new wt:" in output
    assert "Checkout plan #99:" in output
    assert "Dispatch to queue:" in output


def test_format_next_steps_plain_contains_implement() -> None:
    """format_next_steps_plain includes implement commands."""
    output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
    assert "erk implement" in output
    assert "erk implement -d" in output


def test_format_next_steps_plain_contains_checkout() -> None:
    """format_next_steps_plain includes checkout commands."""
    output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
    assert "erk br co --for-plan 99" in output
    assert "erk br co --new-slot --for-plan 99" in output

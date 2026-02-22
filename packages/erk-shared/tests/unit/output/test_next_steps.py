"""Tests for next_steps formatting."""

from erk_shared.output.next_steps import (
    DraftPRNextSteps,
    IssueNextSteps,
    format_draft_pr_next_steps_plain,
    format_next_steps_plain,
)


def test_draft_pr_next_steps_constructs_with_both_params() -> None:
    """DraftPRNextSteps constructs correctly with pr_number and branch_name."""
    s = DraftPRNextSteps(pr_number=42, branch_name="plan-feature-foo")
    assert s.pr_number == 42
    assert s.branch_name == "plan-feature-foo"


def test_draft_pr_next_steps_checkout_and_implement_uses_branch_name() -> None:
    """checkout_and_implement uses branch_name, not pr_number."""
    s = DraftPRNextSteps(pr_number=42, branch_name="plan-feature-foo")
    assert "plan-feature-foo" in s.checkout_and_implement
    assert "42" not in s.checkout_and_implement


def test_draft_pr_next_steps_prepare_uses_branch_name() -> None:
    """prepare uses branch_name directly."""
    s = DraftPRNextSteps(pr_number=42, branch_name="plan-feature-foo")
    assert s.prepare == "erk br co plan-feature-foo"


def test_issue_next_steps_prepare_uses_co() -> None:
    """IssueNextSteps.prepare uses erk br co --for-plan."""
    s = IssueNextSteps(issue_number=99)
    assert s.prepare == "erk br co --for-plan 99"


def test_format_draft_pr_next_steps_plain_uses_branch_name() -> None:
    """format_draft_pr_next_steps_plain uses branch name for prepare commands."""
    output = format_draft_pr_next_steps_plain(42, branch_name="plan-feature-foo")
    assert "erk br co plan-feature-foo" in output
    assert 'source "$(erk br co plan-feature-foo --script)"' in output


def test_format_next_steps_plain_uses_co() -> None:
    """format_next_steps_plain uses erk br co --for-plan."""
    output = format_next_steps_plain(99)
    assert "erk br co --for-plan 99" in output
    assert "erk br create" not in output

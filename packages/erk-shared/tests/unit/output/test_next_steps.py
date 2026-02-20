"""Tests for next_steps formatting."""
from erk_shared.output.next_steps import DraftPRNextSteps, format_draft_pr_next_steps_plain


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


def test_format_draft_pr_next_steps_plain_contains_branch_name() -> None:
    """format_draft_pr_next_steps_plain includes branch name in checkout command."""
    output = format_draft_pr_next_steps_plain(42, branch_name="plan-feature-foo")
    assert "plan-feature-foo" in output
    assert "erk br co" in output

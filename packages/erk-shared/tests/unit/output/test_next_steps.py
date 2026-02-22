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


def test_draft_pr_next_steps_prepare_uses_pr_number() -> None:
    """prepare uses --for-plan with pr_number."""
    s = DraftPRNextSteps(pr_number=42, branch_name="plan-feature-foo")
    assert s.prepare == "erk br co --for-plan 42"


def test_issue_next_steps_prepare_uses_co() -> None:
    """IssueNextSteps.prepare uses erk br co --for-plan."""
    s = IssueNextSteps(issue_number=99)
    assert s.prepare == "erk br co --for-plan 99"


def test_format_draft_pr_next_steps_plain_uses_for_plan() -> None:
    """format_draft_pr_next_steps_plain uses --for-plan command."""
    output = format_draft_pr_next_steps_plain(42, branch_name="plan-feature-foo", on_trunk=False)
    assert "erk br co --for-plan 42" in output
    assert 'source "$(erk br co --for-plan 42 --script)"' in output


def test_format_next_steps_plain_uses_co() -> None:
    """format_next_steps_plain uses erk br co --for-plan."""
    output = format_next_steps_plain(99, on_trunk=False)
    assert "erk br co --for-plan 99" in output
    assert "erk br create" not in output


def test_format_next_steps_plain_on_trunk_recommends_new_slot() -> None:
    """on_trunk=True shows 'New slot (recommended)' first."""
    output = format_next_steps_plain(99, on_trunk=True)
    new_slot_pos = output.index("New slot (recommended")
    same_slot_pos = output.index("Same slot:")
    assert new_slot_pos < same_slot_pos


def test_format_next_steps_plain_in_slot_recommends_same_slot() -> None:
    """on_trunk=False shows 'Same slot (recommended)' first."""
    output = format_next_steps_plain(99, on_trunk=False)
    same_slot_pos = output.index("Same slot (recommended")
    new_slot_pos = output.index("New slot:")
    assert same_slot_pos < new_slot_pos


def test_format_draft_pr_next_steps_plain_on_trunk_recommends_new_slot() -> None:
    """Draft PR: on_trunk=True shows 'New slot (recommended)' first."""
    output = format_draft_pr_next_steps_plain(42, branch_name="plan-feature-foo", on_trunk=True)
    new_slot_pos = output.index("New slot (recommended")
    same_slot_pos = output.index("Same slot:")
    assert new_slot_pos < same_slot_pos


def test_format_draft_pr_next_steps_plain_in_slot_recommends_same_slot() -> None:
    """Draft PR: on_trunk=False shows 'Same slot (recommended)' first."""
    output = format_draft_pr_next_steps_plain(42, branch_name="plan-feature-foo", on_trunk=False)
    same_slot_pos = output.index("Same slot (recommended")
    new_slot_pos = output.index("New slot:")
    assert same_slot_pos < new_slot_pos
